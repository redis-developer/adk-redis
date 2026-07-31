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

"""Tests for adk_redis.cache._provider."""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import warnings

import pytest

pytest.importorskip("redisvl")

from adk_redis.cache._provider import BaseCacheProvider
from adk_redis.cache._provider import CacheEntry
from adk_redis.cache._provider import LangCacheProvider
from adk_redis.cache._provider import LangCacheProviderConfig
from adk_redis.cache._provider import RedisVLCacheProvider
from adk_redis.cache._provider import RedisVLCacheProviderConfig


class TestRedisVLCacheProviderImportPath:
  """Provider must use the canonical redisvl.extensions.cache.llm path.

  redisvl 0.16+ deprecated redisvl.extensions.llmcache. The provider
  must source SemanticCache from the new location so no DeprecationWarning
  is raised when callers construct it.
  """

  def test_construction_does_not_emit_deprecation_warning(
      self, mock_vectorizer
  ):
    """RedisVLCacheProvider construction must not trip DeprecationWarning."""
    config = RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379",
        name="test_cache",
        ttl=60,
    )

    with patch(
        "redisvl.extensions.cache.llm.SemanticCache"
    ) as mock_semantic_cache:
      mock_semantic_cache.return_value = MagicMock()
      with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    mock_semantic_cache.assert_called_once()

  def test_construction_passes_expected_kwargs(self, mock_vectorizer):
    """Config values flow through to SemanticCache."""
    config = RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379/0",
        name="my_cache",
        ttl=120,
        distance_threshold=0.2,
    )

    with patch(
        "redisvl.extensions.cache.llm.SemanticCache"
    ) as mock_semantic_cache:
      RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    _, kwargs = mock_semantic_cache.call_args
    assert kwargs["name"] == "my_cache"
    assert kwargs["redis_url"] == "redis://localhost:6379/0"
    assert kwargs["ttl"] == 120
    assert kwargs["distance_threshold"] == 0.2
    assert kwargs["vectorizer"] is mock_vectorizer
    assert kwargs["overwrite"] is True


class TestBaseCacheProviderContract:
  """The abstract provider contract includes targeted invalidation."""

  def test_delete_by_id_is_abstract(self):
    """A subclass missing delete_by_id cannot be instantiated."""

    class IncompleteProvider(BaseCacheProvider):

      async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
        return None

      async def store(
          self,
          prompt: str,
          response: str,
          metadata: Optional[dict[str, Any]] = None,
          **kwargs: Any,
      ) -> Optional[str]:
        return None

      async def clear(self, **kwargs: Any) -> None:
        pass

      async def close(self) -> None:
        pass

    with pytest.raises(TypeError, match="delete_by_id"):
      IncompleteProvider()


def _make_langcache_provider() -> tuple[LangCacheProvider, MagicMock]:
  """Build a LangCacheProvider around a mocked LangCacheSemanticCache."""
  config = LangCacheProviderConfig(cache_id="cache-1", api_key="secret")
  with patch("redisvl.extensions.cache.llm.LangCacheSemanticCache") as mock_cls:
    mock_cache = MagicMock()
    mock_cache.acheck = AsyncMock(return_value=[])
    mock_cache.astore = AsyncMock(return_value="")
    mock_cache.adelete_by_id = AsyncMock(return_value=None)
    mock_cls.return_value = mock_cache
    provider = LangCacheProvider(config)
  return provider, mock_cache


class TestLangCacheProviderEntryIds:
  """LangCacheProvider surfaces entry IDs and targeted invalidation."""

  async def test_check_surfaces_entry_id(self):
    """check() preserves the LangCache hit's entry_id on CacheEntry."""
    provider, mock_cache = _make_langcache_provider()
    mock_cache.acheck.return_value = [
        {
            "entry_id": "entry-abc",
            "prompt": "What is Redis?",
            "response": "An in-memory data store.",
            "vector_distance": 0.05,
            "metadata": {"source": "docs"},
        }
    ]

    entry = await provider.check("What is Redis?")

    assert entry is not None
    assert entry.entry_id == "entry-abc"
    assert entry.response == "An in-memory data store."
    assert entry.metadata == {"source": "docs"}

  async def test_store_returns_entry_id(self):
    """store() returns the entry ID reported by the backend."""
    provider, mock_cache = _make_langcache_provider()
    mock_cache.astore.return_value = "entry-new"

    entry_id = await provider.store("prompt", "response")

    assert entry_id == "entry-new"

  async def test_delete_by_id_calls_backend_with_exact_id(self):
    """delete_by_id() forwards the exact entry ID to the backend."""
    provider, mock_cache = _make_langcache_provider()

    await provider.delete_by_id("entry-abc")

    mock_cache.adelete_by_id.assert_awaited_once_with("entry-abc")

  async def test_delete_one_of_two_similar_entries_leaves_other_intact(self):
    """Deleting one returned ID retires only that entry (issue #22)."""
    provider, mock_cache = _make_langcache_provider()

    entries: dict[str, dict[str, Any]] = {}
    deleted_ids: list[str] = []

    async def fake_astore(prompt, response, metadata=None, **kwargs):
      entry_id = f"entry-{len(entries) + 1}"
      entries[entry_id] = {
          "entry_id": entry_id,
          "prompt": prompt,
          "response": response,
          "vector_distance": 0.0,
          "metadata": metadata,
      }
      return entry_id

    async def fake_acheck(prompt, **kwargs):
      return [hit for hit in entries.values() if hit["prompt"] == prompt]

    async def fake_adelete_by_id(entry_id):
      deleted_ids.append(entry_id)
      entries.pop(entry_id, None)

    mock_cache.astore.side_effect = fake_astore
    mock_cache.acheck.side_effect = fake_acheck
    mock_cache.adelete_by_id.side_effect = fake_adelete_by_id

    stale_id = await provider.store(
        "What is our refund policy?", "30 days, policy doc v12."
    )
    fresh_id = await provider.store(
        "What's the refund policy?", "60 days, policy doc v13."
    )
    assert stale_id != fresh_id

    await provider.delete_by_id(stale_id)

    assert deleted_ids == [stale_id]
    assert await provider.check("What is our refund policy?") is None
    survivor = await provider.check("What's the refund policy?")
    assert survivor is not None
    assert survivor.entry_id == fresh_id
    assert survivor.response == "60 days, policy doc v13."


def _make_redisvl_provider(
    mock_vectorizer: MagicMock,
) -> tuple[RedisVLCacheProvider, MagicMock]:
  """Build a RedisVLCacheProvider around a mocked SemanticCache."""
  config = RedisVLCacheProviderConfig(name="test_cache")
  with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
    mock_cache = MagicMock()
    mock_cls.return_value = mock_cache
    provider = RedisVLCacheProvider(config, vectorizer=mock_vectorizer)
  return provider, mock_cache


class TestRedisVLCacheProviderEntryIds:
  """RedisVLCacheProvider uses full Redis keys as entry IDs."""

  async def test_check_surfaces_redis_key_as_entry_id(self, mock_vectorizer):
    """check() surfaces the hit's Redis key on CacheEntry.entry_id."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)
    mock_cache.check.return_value = [
        {
            "response": "An in-memory data store.",
            "vector_distance": 0.08,
            "entry_id": "abc123",
            "key": "test_cache:abc123",
        }
    ]

    entry = await provider.check("What is Redis?")

    assert entry is not None
    assert entry.entry_id == "test_cache:abc123"
    assert entry.response == "An in-memory data store."

  async def test_store_returns_redis_key(self, mock_vectorizer):
    """store() returns the Redis key reported by the backend."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)
    mock_cache.store.return_value = "test_cache:abc123"

    entry_id = await provider.store("prompt", "response")

    assert entry_id == "test_cache:abc123"

  async def test_delete_by_id_drops_exact_key(self, mock_vectorizer):
    """delete_by_id() drops exactly the given Redis key."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)

    await provider.delete_by_id("test_cache:abc123")

    mock_cache.drop.assert_called_once_with(keys=["test_cache:abc123"])
