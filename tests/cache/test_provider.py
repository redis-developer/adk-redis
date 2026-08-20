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

import inspect
from typing import Any, Optional
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import warnings

import pytest

pytest.importorskip("redisvl")

from redisvl.extensions.cache.llm import SemanticCache

from adk_redis.cache._provider import _redisvl_supports_create_index
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
    assert kwargs["overwrite"] is False
    # create_index is only forwarded when disabled, so the default path
    # stays compatible with redisvl releases predating the flag.
    assert "create_index" not in kwargs


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


@pytest.mark.asyncio
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


@pytest.mark.asyncio
class TestRedisVLCacheProviderEntryIds:
  """RedisVLCacheProvider surfaces RedisVL entry IDs."""

  async def test_check_surfaces_entry_id(self, mock_vectorizer):
    """check() surfaces the hit's RedisVL entry ID."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)
    mock_cache.check.return_value = [
        {
            "response": "An in-memory data store.",
            "vector_distance": 0.08,
            "entry_id": "abc123",
        }
    ]

    entry = await provider.check("What is Redis?")

    assert entry is not None
    assert entry.entry_id == "abc123"
    assert entry.response == "An in-memory data store."

  async def test_store_returns_entry_id(self, mock_vectorizer):
    """store() normalizes the backend Redis key to its entry ID."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)
    mock_cache.store.return_value = "test_cache:abc123"

    entry_id = await provider.store("prompt", "response")

    assert entry_id == "abc123"

  async def test_delete_by_id_drops_exact_entry_id(self, mock_vectorizer):
    """delete_by_id() drops exactly the given RedisVL entry ID."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)

    await provider.delete_by_id("abc123")

    mock_cache.drop.assert_called_once_with(ids=["abc123"])


class TestRedisVLCacheProviderCreateIndex:
  """create_index lets the provider attach to an external index.

  redisvl 0.26.0 added create_index. With create_index=False the RedisVL
  cache issues no index command at construction, so the provider works on a
  credential that is denied FT.INFO and FT.CREATE.
  """

  def test_create_index_false_is_forwarded(self, mock_vectorizer):
    """create_index=False reaches SemanticCache with overwrite off."""
    config = RedisVLCacheProviderConfig(
        name="external_cache", create_index=False
    )

    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    _, kwargs = mock_cls.call_args
    assert kwargs["create_index"] is False
    assert kwargs["overwrite"] is False
    assert kwargs["name"] == "external_cache"

  def test_create_index_false_with_overwrite_is_rejected(self, mock_vectorizer):
    """The contradiction is refused before any index command is issued."""
    config = RedisVLCacheProviderConfig(create_index=False, overwrite=True)

    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      with pytest.raises(ValueError) as excinfo:
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    message = str(excinfo.value)
    assert "create_index=False" in message
    assert "overwrite=True" in message
    mock_cls.assert_not_called()

  def test_create_index_false_requires_redisvl_026(self, mock_vectorizer):
    """An older redisvl reports the required version, not an AttributeError."""
    config = RedisVLCacheProviderConfig(create_index=False)

    with patch(
        "adk_redis.cache._provider._redisvl_supports_create_index",
        return_value=False,
    ):
      with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
        with pytest.raises(ImportError) as excinfo:
          RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    assert "redisvl>=0.26.0" in str(excinfo.value)
    mock_cls.assert_not_called()

  def test_default_config_works_on_older_redisvl(self, mock_vectorizer):
    """The default path never sends create_index, so old releases still work."""
    config = RedisVLCacheProviderConfig()

    with patch(
        "adk_redis.cache._provider._redisvl_supports_create_index",
        return_value=False,
    ):
      with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    _, kwargs = mock_cls.call_args
    assert "create_index" not in kwargs

  def test_redisvl_value_error_is_reraised_with_config_guidance(
      self, mock_vectorizer
  ):
    """A RedisVL rejection names the config fields that control the index."""
    config = RedisVLCacheProviderConfig(name="mismatched")

    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      mock_cls.side_effect = ValueError(
          "Existing index mismatched schema does not match."
      )
      with pytest.raises(ValueError) as excinfo:
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    message = str(excinfo.value)
    assert "mismatched" in message
    assert "RedisVLCacheProviderConfig" in message
    assert "overwrite" in message
    assert isinstance(excinfo.value.__cause__, ValueError)

  def test_supports_create_index_matches_installed_redisvl(self):
    """The capability probe agrees with the installed SemanticCache."""
    signature = inspect.signature(SemanticCache.__init__)
    assert _redisvl_supports_create_index() == (
        "create_index" in signature.parameters
    )


@pytest.mark.asyncio
class TestRedisVLCacheProviderClear:
  """clear() must work for both managed and externally managed indices."""

  async def test_clear_delegates_to_redisvl_when_managed(self, mock_vectorizer):
    """The default path still calls SemanticCache.clear()."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)

    await provider.clear()

    mock_cache.clear.assert_called_once_with()

  async def test_clear_scans_keys_for_external_index(self, mock_vectorizer):
    """An external index is left in place while its entries are deleted."""
    config = RedisVLCacheProviderConfig(
        name="external_cache", create_index=False
    )
    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      mock_cache = MagicMock()
      mock_cache._get_redis_client.return_value.scan_iter.return_value = iter(
          ["external_cache:a", "external_cache:b"]
      )
      mock_cls.return_value = mock_cache
      provider = RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    await provider.clear()

    client = mock_cache._get_redis_client.return_value
    _, scan_kwargs = client.scan_iter.call_args
    assert scan_kwargs["match"] == "external_cache:*"
    client.delete.assert_called_once_with(
        "external_cache:a", "external_cache:b"
    )
    mock_cache.clear.assert_not_called()

  async def test_delete_by_id_still_works_for_external_index(
      self, mock_vectorizer
  ):
    """Targeted invalidation needs no index command, so it stays available."""
    config = RedisVLCacheProviderConfig(create_index=False)
    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      mock_cache = MagicMock()
      mock_cls.return_value = mock_cache
      provider = RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    await provider.delete_by_id("abc123")

    mock_cache.drop.assert_called_once_with(ids=["abc123"])

  async def test_close_disconnects_without_a_live_client(self, mock_vectorizer):
    """close() must not assume a client exists.

    With create_index=False construction sends no command, so RedisVL may
    never have opened a connection by the time close() runs.
    """
    config = RedisVLCacheProviderConfig(create_index=False)
    with patch("redisvl.extensions.cache.llm.SemanticCache") as mock_cls:
      mock_cache = MagicMock()
      mock_cls.return_value = mock_cache
      provider = RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    await provider.close()

    mock_cache.disconnect.assert_called_once_with()
