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
from urllib.parse import urlparse
import uuid

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
    """An externally provisioned index serves check(), store(), and clear()."""
    # Stand in for the platform team: provision the index out of band, then
    # attach a second provider that is told not to manage it.
    owner_config = RedisVLCacheProviderConfig(
        redis_url=redis_url, name=unique_index_name, ttl=60
    )
    owner = RedisVLCacheProvider(owner_config, vectorizer=vectorizer)
    assert unique_index_name in _index_names(redis_url)

    attached_config = RedisVLCacheProviderConfig(
        redis_url=redis_url,
        name=unique_index_name,
        ttl=60,
        create_index=False,
    )
    attached = RedisVLCacheProvider(attached_config, vectorizer=vectorizer)
    try:
      entry_id = await attached.store("hello world", "hi there")
      hit = await attached.check("hello world")
      assert hit is not None
      assert hit.response == "hi there"
      assert entry_id is not None

      # clear() must remove entries without dropping the external index.
      await attached.clear()
      assert await attached.check("hello world") is None
      assert unique_index_name in _index_names(redis_url)
    finally:
      await attached.close()
      await owner.clear()
      await owner.close()

  @pytest.mark.asyncio
  async def test_delete_by_id_on_pre_provisioned_index(
      self, redis_url: str, vectorizer, unique_index_name
  ):
    """Targeted invalidation works while the index is externally managed."""
    owner_config = RedisVLCacheProviderConfig(
        redis_url=redis_url, name=unique_index_name, ttl=60
    )
    owner = RedisVLCacheProvider(owner_config, vectorizer=vectorizer)
    attached_config = RedisVLCacheProviderConfig(
        redis_url=redis_url,
        name=unique_index_name,
        ttl=60,
        create_index=False,
    )
    attached = RedisVLCacheProvider(attached_config, vectorizer=vectorizer)
    try:
      entry_id = await attached.store("what is redis", "a data store")
      assert entry_id is not None

      await attached.delete_by_id(entry_id)

      assert await attached.check("what is redis") is None
      assert unique_index_name in _index_names(redis_url)
    finally:
      await attached.close()
      await owner.clear()
      await owner.close()


@pytest.fixture
def restricted_acl_url(redis_url: str):
  """Yield a Redis URL for a user granted +@read +@write and no @search.

  This is the credential shape reported by customers whose search indices
  are provisioned by a platform team: FT.INFO and FT.CREATE are denied,
  while FT.SEARCH remains reachable through the @read category.
  """
  admin = redis.Redis.from_url(redis_url)
  username = f"adk_redis_it_{uuid.uuid4().hex[:8]}"
  password = "it-secret"
  try:
    admin.execute_command(
        "ACL",
        "SETUSER",
        username,
        "on",
        f">{password}",
        "~*",
        "+@read",
        "+@write",
    )
  except redis.exceptions.ResponseError as e:
    admin.close()
    pytest.skip(f"cannot provision an ACL user on this Redis: {e}")

  parsed = urlparse(redis_url)
  netloc = f"{username}:{password}@{parsed.hostname}"
  if parsed.port:
    netloc = f"{netloc}:{parsed.port}"
  try:
    yield parsed._replace(netloc=netloc).geturl()
  finally:
    admin.execute_command("ACL", "DELUSER", username)
    admin.close()


@REQUIRES_REDIS
class TestRedisVLCacheProviderRestrictedAcl:
  """The cache must attach to an index on a credential denied @search."""

  @pytest.mark.asyncio
  async def test_default_path_is_denied_without_search_grant(
      self, restricted_acl_url: str, vectorizer, unique_index_name
  ):
    """create_index=True cannot even probe the index on this credential."""
    config = RedisVLCacheProviderConfig(
        redis_url=restricted_acl_url, name=unique_index_name, ttl=60
    )

    with pytest.raises(RedisSearchError) as excinfo:
      RedisVLCacheProvider(config, vectorizer=vectorizer)

    assert "FT.INFO" in str(excinfo.value)

  @pytest.mark.asyncio
  async def test_round_trip_on_restricted_acl(
      self,
      redis_url: str,
      restricted_acl_url: str,
      vectorizer,
      unique_index_name,
  ):
    """A pre-provisioned index serves the full runtime path on +@read."""
    # The platform team provisions the index with a privileged credential.
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

      # clear() takes the prefix scan path, needing no index command.
      await attached.store("another prompt", "another response")
      await attached.clear()
      assert await attached.check("another prompt") is None
      assert unique_index_name in _index_names(redis_url)
    finally:
      await attached.close()
      await owner.clear()
      await owner.close()
