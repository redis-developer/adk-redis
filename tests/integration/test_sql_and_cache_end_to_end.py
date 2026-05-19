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
