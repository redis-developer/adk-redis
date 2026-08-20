# Copyright 2025 Redis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""End-to-end integration tests for SQLSearchTool and the cache provider."""

from __future__ import annotations

import hashlib
import math
from unittest.mock import MagicMock

import pytest
import redis
from redisvl.exceptions import RedisSearchError
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema
from redisvl.utils.vectorize.text.custom import CustomTextVectorizer

from adk_redis import RedisSQLSearchTool
from adk_redis import RedisVLCacheProvider
from adk_redis import RedisVLCacheProviderConfig
from tests.integration.conftest import REQUIRES_REDIS

_VECTOR_DIM = 16


def _embed(text: str) -> list[float]:
  parts: list[float] = []
  for i in range(_VECTOR_DIM):
    h = hashlib.sha256(f"{i}:{text}".encode()).digest()
    parts.append(int.from_bytes(h[:4], "big") / 2**32 - 0.5)
  norm = math.sqrt(sum(p * p for p in parts)) or 1.0
  return [p / norm for p in parts]


@pytest.fixture
def vectorizer() -> CustomTextVectorizer:
  return CustomTextVectorizer(
      embed=_embed,
      embed_many=lambda xs: [_embed(x) for x in xs],
      dtype="float32",
  )


@pytest.fixture
def catalog_index(redis_url: str, unique_index_name: str):
  """Build a small product catalog index for SQL tests."""
  schema = IndexSchema.from_dict(
      {
          "index": {
              "name": unique_index_name,
              "prefix": f"{unique_index_name}:doc",
              "storage_type": "hash",
          },
          "fields": [
              {"name": "title", "type": "text"},
              {"name": "category", "type": "tag"},
              {"name": "price", "type": "numeric"},
          ],
      }
  )
  idx = SearchIndex(schema=schema, redis_url=redis_url)
  idx.create(overwrite=True)
  idx.load(
      [
          {"title": "Headphones", "category": "electronics", "price": 199},
          {"title": "Earbuds", "category": "electronics", "price": 25},
          {"title": "Yoga Mat", "category": "fitness", "price": 35},
      ]
  )
  yield idx
  try:
    idx.delete(drop=True)
  except Exception:
    pass


@REQUIRES_REDIS
class TestSQLSearchEndToEnd:

  @pytest.mark.asyncio
  async def test_sql_select_with_where(self, catalog_index, unique_index_name):
    tool = RedisSQLSearchTool(index=catalog_index)
    result = await tool.run_async(
        args={
            "sql": (
                f"SELECT title, price, category FROM {unique_index_name} "
                "WHERE category = 'electronics' AND price < 100"
            )
        },
        tool_context=MagicMock(),
    )

    assert result["status"] == "success", result.get("error")
    titles = [r["title"] for r in result["results"]]
    assert "Earbuds" in titles
    assert "Headphones" not in titles
    assert "Yoga Mat" not in titles

  @pytest.mark.asyncio
  async def test_sql_select_with_params(self, catalog_index, unique_index_name):
    tool = RedisSQLSearchTool(index=catalog_index)
    result = await tool.run_async(
        args={
            "sql": (
                f"SELECT title, price FROM {unique_index_name} "
                "WHERE price < :max_price"
            ),
            "params": {"max_price": 50},
        },
        tool_context=MagicMock(),
    )

    assert result["status"] == "success", result.get("error")
    prices = [r["price"] for r in result["results"]]
    assert all(int(p) < 50 for p in prices)


@REQUIRES_REDIS
class TestRedisVLCacheProviderEndToEnd:
  """The cache provider must round-trip a prompt against real Redis."""

  @pytest.mark.asyncio
  async def test_cache_round_trip(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    config = RedisVLCacheProviderConfig(
        redis_url=redis_url,
        name=unique_index_name,
        ttl=60,
        distance_threshold=0.1,
    )
    provider = RedisVLCacheProvider(config, vectorizer=vectorizer)
    try:
      await provider.store("hello world", "hi there")
      hit = await provider.check("hello world")
      assert hit is not None
      assert hit.response == "hi there"
    finally:
      await provider.clear()
      await provider.close()


def _index_names(redis_url: str) -> set[str]:
  """Return the search index names that exist on the server."""
  client = redis.Redis.from_url(redis_url)
  try:
    return {
        name.decode() if isinstance(name, bytes) else str(name)
        for name in client.execute_command("FT._LIST")
    }
  finally:
    client.close()


def _provision_cache_index(
    redis_url: str, name: str, *, dims: int, prefix: str | None = None
) -> None:
  """Create a cache index out of band, standing in for a platform team.

  Args:
    redis_url: Connection string used to create the index.
    name: Index name, which the provider must be pointed at.
    dims: Vector dimensions to declare for the prompt vector.
    prefix: Key prefix to index. Defaults to the name, matching RedisVL.
  """
  schema = IndexSchema.from_dict(
      {
          "index": {
              "name": name,
              "prefix": prefix if prefix is not None else name,
              "storage_type": "hash",
          },
          "fields": [
              {"name": "prompt", "type": "text"},
              {"name": "response", "type": "text"},
              {
                  "name": "prompt_vector",
                  "type": "vector",
                  "attrs": {
                      "dims": dims,
                      "algorithm": "flat",
                      "datatype": "float32",
                      "distance_metric": "cosine",
                  },
              },
          ],
      }
  )
  index = SearchIndex(schema, redis_url=redis_url)
  index.create(overwrite=True)


@REQUIRES_REDIS
class TestRedisVLCacheProviderExternalIndex:
  """create_index=False attaches to an index adk-redis did not create."""

  @pytest.mark.asyncio
  async def test_construction_issues_no_index_command(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """A missing index stays missing, proving no FT.CREATE was sent."""
    config = RedisVLCacheProviderConfig(
        redis_url=redis_url,
        name=unique_index_name,
        ttl=60,
        create_index=False,
    )

    provider = RedisVLCacheProvider(config, vectorizer=vectorizer)
    try:
      assert unique_index_name not in _index_names(redis_url)
    finally:
      await provider.close()

  @pytest.mark.asyncio
  async def test_round_trip_against_pre_provisioned_index(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """An externally provisioned index serves the whole runtime path."""
    owner_config = RedisVLCacheProviderConfig(
        redis_url=redis_url, name=unique_index_name, ttl=60
    )
    owner = RedisVLCacheProvider(owner_config, vectorizer=vectorizer)
    assert unique_index_name in _index_names(redis_url)

    attached = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url,
            name=unique_index_name,
            ttl=60,
            create_index=False,
        ),
        vectorizer=vectorizer,
    )
    try:
      entry_id = await attached.store("hello world", "hi there")
      assert entry_id is not None
      hit = await attached.check("hello world")
      assert hit is not None
      assert hit.response == "hi there"

      await attached.delete_by_id(entry_id)
      assert await attached.check("hello world") is None

      # clear() must remove entries without dropping the external index.
      await attached.store("another prompt", "another response")
      await attached.clear()
      assert await attached.check("another prompt") is None
      assert unique_index_name in _index_names(redis_url)
    finally:
      await attached.close()
      await owner.clear()
      await owner.close()

  @pytest.mark.asyncio
  async def test_clear_leaves_a_neighbouring_cache_intact(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """clear() must only delete keys under its own cache prefix.

    Cache entry keys are "<name>:<entry_id>", so a scan pattern missing the
    trailing separator would also delete a "<name>_v2:" cache's entries.
    Note this asserts deletion scope only: RedisVL gives the index itself
    the bare name as its prefix, so a neighbouring cache whose name extends
    this one is visible to both indices.
    """
    neighbour_name = f"{unique_index_name}_v2"
    owner = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url, name=unique_index_name, ttl=60
        ),
        vectorizer=vectorizer,
    )
    neighbour = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url, name=neighbour_name, ttl=60
        ),
        vectorizer=vectorizer,
    )
    attached = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url,
            name=unique_index_name,
            ttl=60,
            create_index=False,
        ),
        vectorizer=vectorizer,
    )
    try:
      await attached.store("shared prompt", "from the first cache")
      await neighbour.store("shared prompt", "from the neighbour")

      client = redis.Redis.from_url(redis_url)
      try:
        await attached.clear()

        assert not list(client.scan_iter(match=f"{unique_index_name}:*"))
        assert list(client.scan_iter(match=f"{neighbour_name}:*"))
      finally:
        client.close()
      survivor = await neighbour.check("shared prompt")
      assert survivor is not None
      assert survivor.response == "from the neighbour"
    finally:
      await attached.close()
      await neighbour.clear()
      await neighbour.close()
      await owner.close()

  @pytest.mark.asyncio
  async def test_mismatched_index_misses_silently(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """A mismatched attached index yields misses, not errors.

    This is the failure the guide warns about: entries are written and
    TTLs set, every lookup misses, and nothing raises. Pinned here because
    the docs promise this shape and a future RedisVL could change it.
    """
    # Same name and prefix as the provider expects, wrong vector width.
    _provision_cache_index(redis_url, unique_index_name, dims=384)
    attached = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url,
            name=unique_index_name,
            ttl=60,
            create_index=False,
        ),
        vectorizer=vectorizer,
    )
    try:
      entry_id = await attached.store("what is redis", "a data store")
      assert entry_id is not None
      assert await attached.check("what is redis") is None
    finally:
      await attached.clear()
      await attached.close()

  @pytest.mark.asyncio
  async def test_absent_index_raises_rather_than_missing(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """A wrong index name raises on the first check(), it is not silent."""
    attached = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url,
            name=unique_index_name,
            ttl=60,
            create_index=False,
        ),
        vectorizer=vectorizer,
    )
    try:
      await attached.store("what is redis", "a data store")
      with pytest.raises(RedisSearchError, match="No such index"):
        await attached.check("what is redis")
    finally:
      # The prefix scan needs no index, so it reclaims the written entry.
      await attached.clear()
      await attached.close()

  @pytest.mark.asyncio
  async def test_schema_mismatch_names_the_config_field(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """The managed path reports a drifted schema with a usable remedy.

    This is the error the overwrite=False default exists to surface, so it
    is asserted against a real index rather than a mocked exception.
    """
    _provision_cache_index(redis_url, unique_index_name, dims=384)
    try:
      with pytest.raises(ValueError) as excinfo:
        RedisVLCacheProvider(
            RedisVLCacheProviderConfig(
                redis_url=redis_url, name=unique_index_name, ttl=60
            ),
            vectorizer=vectorizer,
        )

      message = str(excinfo.value)
      assert unique_index_name in message
      assert "overwrite=True" in message
    finally:
      redis.Redis.from_url(redis_url).execute_command(
          "FT.DROPINDEX", unique_index_name, "DD"
      )

  @pytest.mark.asyncio
  async def test_overwrite_rebuilds_a_drifted_index(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """overwrite=True is the documented escape hatch for a drifted schema."""
    _provision_cache_index(redis_url, unique_index_name, dims=384)
    provider = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url,
            name=unique_index_name,
            ttl=60,
            overwrite=True,
        ),
        vectorizer=vectorizer,
    )
    try:
      await provider.store("what is redis", "a data store")
      hit = await provider.check("what is redis")
      assert hit is not None
      assert hit.response == "a data store"
    finally:
      await provider.clear()
      await provider.close()


@REQUIRES_REDIS
class TestRedisVLCacheProviderRestrictedAcl:
  """The cache must attach to an index on a credential denied @search."""

  @pytest.mark.asyncio
  async def test_default_path_reports_the_denied_command(
      self, restricted_acl_url: str, vectorizer, unique_index_name
  ):
    """create_index=True cannot probe the index, and says what to do."""
    config = RedisVLCacheProviderConfig(
        redis_url=restricted_acl_url, name=unique_index_name, ttl=60
    )

    with pytest.raises(RedisSearchError) as excinfo:
      RedisVLCacheProvider(config, vectorizer=vectorizer)

    message = str(excinfo.value)
    assert "FT.INFO" in message
    assert "create_index=False" in message

  @pytest.mark.asyncio
  async def test_round_trip_on_restricted_acl(
      self,
      redis_url: str,
      restricted_acl_url: str,
      vectorizer,
      unique_index_name,
  ):
    """A pre-provisioned index serves the full runtime path on +@read."""
    owner = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=redis_url, name=unique_index_name, ttl=60
        ),
        vectorizer=vectorizer,
    )
    attached = RedisVLCacheProvider(
        RedisVLCacheProviderConfig(
            redis_url=restricted_acl_url,
            name=unique_index_name,
            ttl=60,
            create_index=False,
        ),
        vectorizer=vectorizer,
    )
    try:
      entry_id = await attached.store("what is redis", "a data store")
      assert entry_id is not None

      # FT.SEARCH carries the @read category, so check() still resolves.
      hit = await attached.check("what is redis")
      assert hit is not None
      assert hit.response == "a data store"

      await attached.delete_by_id(entry_id)
      assert await attached.check("what is redis") is None

      await attached.store("another prompt", "another response")
      await attached.clear()
      assert await attached.check("another prompt") is None
      assert unique_index_name in _index_names(redis_url)
    finally:
      await attached.close()
      await owner.clear()
      await owner.close()
