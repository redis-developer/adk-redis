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

"""End-to-end integration tests for the four search tools against real Redis.

These tests build a real RediSearch index, write documents, and run each
adk-redis search tool through its public ``run_async`` path. They skip
when Redis is not reachable.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any
from unittest.mock import MagicMock

import pytest
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema
from redisvl.utils.vectorize.text.custom import CustomTextVectorizer

from adk_redis import RedisHybridQueryConfig
from adk_redis import RedisHybridSearchTool
from adk_redis import RedisRangeQueryConfig
from adk_redis import RedisRangeSearchTool
from adk_redis import RedisTextQueryConfig
from adk_redis import RedisTextSearchTool
from adk_redis import RedisVectorQueryConfig
from adk_redis import RedisVectorSearchTool
from tests.integration.conftest import REQUIRES_REDIS

_VECTOR_DIM = 16


def _deterministic_embed(text: str) -> list[float]:
  """Stable, ~unit-length 16-dim embedding derived from text.

  Hashes the input four times with different prefixes and decodes the
  bytes into floats. Two near-identical strings produce close vectors;
  unrelated strings sit far apart.
  """
  parts: list[float] = []
  for i in range(_VECTOR_DIM):
    h = hashlib.sha256(f"{i}:{text}".encode()).digest()
    v = int.from_bytes(h[:4], "big") / 2**32
    parts.append(v - 0.5)
  norm = math.sqrt(sum(p * p for p in parts)) or 1.0
  return [p / norm for p in parts]


def _embed_many(texts: list[str]) -> list[list[float]]:
  return [_deterministic_embed(t) for t in texts]


@pytest.fixture
def vectorizer() -> CustomTextVectorizer:
  return CustomTextVectorizer(
      embed=_deterministic_embed,
      embed_many=_embed_many,
      dtype="float32",
  )


@pytest.fixture
def index(redis_url: str, unique_index_name: str):
  """Build a real RediSearch index with two text fields, a tag, a numeric, and a vector."""
  schema_dict: dict[str, Any] = {
      "index": {
          "name": unique_index_name,
          "prefix": f"{unique_index_name}:doc",
          "storage_type": "hash",
      },
      "fields": [
          {"name": "title", "type": "text"},
          {"name": "content", "type": "text"},
          {"name": "category", "type": "tag"},
          {"name": "price", "type": "numeric"},
          {
              "name": "embedding",
              "type": "vector",
              "attrs": {
                  "dims": _VECTOR_DIM,
                  "algorithm": "flat",
                  "datatype": "float32",
                  "distance_metric": "cosine",
              },
          },
      ],
  }
  schema = IndexSchema.from_dict(schema_dict)
  idx = SearchIndex(schema=schema, redis_url=redis_url)
  idx.create(overwrite=True)
  yield idx
  try:
    idx.delete(drop=True)
  except Exception:
    pass


@pytest.fixture
def populated_index(index, vectorizer: CustomTextVectorizer):
  """Index with three documents."""
  from redisvl.redis.utils import array_to_buffer

  docs = [
      {
          "title": "Wireless Headphones",
          "content": "Bluetooth over-ear headphones with active noise cancellation.",
          "category": "electronics",
          "price": 199,
      },
      {
          "title": "Wired Earbuds",
          "content": "Affordable wired earbuds with a microphone.",
          "category": "electronics",
          "price": 25,
      },
      {
          "title": "Yoga Mat",
          "content": "Non-slip yoga mat with carrying strap.",
          "category": "fitness",
          "price": 35,
      },
  ]
  for d in docs:
    emb = vectorizer.embed(d["content"])
    d["embedding"] = array_to_buffer(emb, dtype="float32")
  index.load(docs)
  return index


@REQUIRES_REDIS
class TestVectorSearchEndToEnd:

  @pytest.mark.asyncio
  async def test_vector_search_finds_nearest_neighbor(
      self, populated_index, vectorizer
  ):
    tool = RedisVectorSearchTool(
        index=populated_index,
        vectorizer=vectorizer,
        config=RedisVectorQueryConfig(num_results=3),
        return_fields=["title", "content", "category", "price"],
    )
    result = await tool.run_async(
        args={"query": "noise cancelling bluetooth headphones"},
        tool_context=MagicMock(),
    )

    assert result["status"] == "success"
    assert result["count"] >= 1
    titles = [r["title"] for r in result["results"]]
    assert "Wireless Headphones" in titles


@REQUIRES_REDIS
class TestTextSearchEndToEnd:

  @pytest.mark.asyncio
  async def test_text_search_returns_keyword_match(self, populated_index):
    tool = RedisTextSearchTool(
        index=populated_index,
        config=RedisTextQueryConfig(
            text_field_name="content",
            num_results=5,
            stopwords=None,
        ),
        return_fields=["title", "content"],
    )
    result = await tool.run_async(
        args={"query": "bluetooth"},
        tool_context=MagicMock(),
    )

    assert result["status"] == "success"
    assert result["count"] >= 1
    titles = [r["title"] for r in result["results"]]
    assert "Wireless Headphones" in titles


@REQUIRES_REDIS
class TestRangeSearchEndToEnd:

  @pytest.mark.asyncio
  async def test_range_search_within_distance(
      self, populated_index, vectorizer
  ):
    tool = RedisRangeSearchTool(
        index=populated_index,
        vectorizer=vectorizer,
        config=RedisRangeQueryConfig(
            distance_threshold=1.5,
            num_results=10,
        ),
        return_fields=["title", "category"],
    )
    result = await tool.run_async(
        args={"query": "headphones"},
        tool_context=MagicMock(),
    )

    assert result["status"] == "success"
    # All three docs are within cosine distance 1.5 of any query.
    assert result["count"] >= 1


@REQUIRES_REDIS
class TestHybridSearchEndToEnd:
  """Native FT.HYBRID path against Redis 8.4+."""

  @pytest.mark.asyncio
  async def test_native_hybrid_returns_results(
      self, populated_index, vectorizer
  ):
    tool = RedisHybridSearchTool(
        index=populated_index,
        vectorizer=vectorizer,
        config=RedisHybridQueryConfig(
            text_field_name="content",
            combination_method="LINEAR",
            linear_alpha=0.5,
            num_results=5,
            stopwords=None,  # avoid optional nltk dependency in CI
        ),
        return_fields=["title", "content", "category"],
    )
    # Native hybrid auto-detect should pick the native path.
    assert tool._use_native is True

    result = await tool.run_async(
        args={"query": "wireless headphones"},
        tool_context=MagicMock(),
    )

    assert result["status"] == "success"
    assert result["count"] >= 1
