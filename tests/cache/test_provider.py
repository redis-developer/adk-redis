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

import importlib.metadata
from typing import Any, Optional
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import warnings

from packaging.requirements import Requirement
import pytest

pytest.importorskip("redisvl")

from redisvl.extensions.cache.llm import SemanticCache

from adk_redis.cache._provider import _accepts_create_index
from adk_redis.cache._provider import _escape_glob
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
    config: Optional[RedisVLCacheProviderConfig] = None,
) -> tuple[RedisVLCacheProvider, MagicMock]:
  """Build a RedisVLCacheProvider around a mocked SemanticCache.

  The mock is spec'd so that a RedisVL release removing a method this
  provider calls fails here rather than in production.
  """
  config = config or RedisVLCacheProviderConfig(name="test_cache")
  with patch(
      "redisvl.extensions.cache.llm.SemanticCache", autospec=True
  ) as mock_cls:
    mock_cache = MagicMock(spec=SemanticCache)
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
    mock_cache._get_prefix.return_value = "test_cache:"

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
  credential that is denied FT.INFO and FT.CREATE. That construction is
  proven against real Redis in the integration suite; these tests cover the
  guards that run before RedisVL is reached.
  """

  def test_create_index_false_with_overwrite_is_rejected(self, mock_vectorizer):
    """The contradiction is refused before any index command is issued."""
    config = RedisVLCacheProviderConfig(create_index=False, overwrite=True)

    with patch(
        "redisvl.extensions.cache.llm.SemanticCache", autospec=True
    ) as mock_cls:
      with pytest.raises(ValueError) as excinfo:
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    message = str(excinfo.value)
    assert "create_index=False" in message
    assert "overwrite=True" in message
    mock_cls.assert_not_called()

  def test_create_index_false_requires_redisvl_026(self, mock_vectorizer):
    """An older redisvl reports the required version, not a silent no-op.

    redisvl 0.18.2 accepts **kwargs, so an unrecognized create_index would
    be swallowed and the provider would manage the index anyway.
    """
    config = RedisVLCacheProviderConfig(create_index=False)

    with patch(
        "adk_redis.cache._provider._accepts_create_index", return_value=False
    ):
      with patch(
          "redisvl.extensions.cache.llm.SemanticCache", autospec=True
      ) as mock_cls:
        with pytest.raises(ValueError) as excinfo:
          RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    assert "redisvl>=0.26.0" in str(excinfo.value)
    mock_cls.assert_not_called()

  def test_default_config_works_on_older_redisvl(self, mock_vectorizer):
    """The default path never sends create_index, so old releases still work."""
    config = RedisVLCacheProviderConfig()

    with patch(
        "adk_redis.cache._provider._accepts_create_index", return_value=False
    ):
      with patch(
          "redisvl.extensions.cache.llm.SemanticCache", autospec=True
      ) as mock_cls:
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    _, kwargs = mock_cls.call_args
    assert "create_index" not in kwargs

  def test_bad_redis_url_error_is_not_relabeled(self, mock_vectorizer):
    """Only a schema mismatch gets index-configuration advice.

    A malformed redis_url already names the field to fix, so rewriting it
    as an index problem would point the caller at the wrong knob.
    """
    config = RedisVLCacheProviderConfig(redis_url="http://not-a-redis-url")
    mock_vectorizer.dims = 384
    mock_vectorizer.dtype = "float32"

    with pytest.raises(ValueError) as excinfo:
      RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    message = str(excinfo.value)
    assert "scheme" in message.lower()
    assert "overwrite" not in message
    assert "create_index" not in message

  def test_probe_reads_the_constructor_signature(self):
    """The probe asks the class it is about to call, not a proxy constant."""

    class WithoutFlag:

      def __init__(self, name: str):
        pass

    assert _accepts_create_index(SemanticCache) is True
    assert _accepts_create_index(WithoutFlag) is False

  def test_escape_glob_neutralizes_metacharacters(self):
    """A cache name cannot widen the SCAN pattern used by clear().

    Unescaped, "cache[ab]:*" matches unrelated cachea: and cacheb: keys
    while missing the cache's own keys, so clear() would delete the wrong
    entries.
    """
    assert _escape_glob("plain_cache") == "plain_cache"
    assert _escape_glob("cache[ab]") == "cache\\[ab\\]"
    assert _escape_glob("ca*che?") == "ca\\*che\\?"


@pytest.mark.asyncio
class TestRedisVLCacheProviderClear:
  """clear() must not take the external path for a managed index."""

  async def test_clear_delegates_to_redisvl_when_managed(self, mock_vectorizer):
    """The default path calls SemanticCache.clear() rather than scanning."""
    provider, mock_cache = _make_redisvl_provider(mock_vectorizer)

    await provider.clear()

    mock_cache.clear.assert_called_once_with()
    mock_cache._get_redis_client.assert_not_called()


def test_version_gate_is_still_load_bearing():
  """Delete the capability probe once the redisvl floor reaches 0.26.0.

  _accepts_create_index and its ValueError branch exist only so the
  declared floor can stay below the release that added create_index. This
  test fails when that is no longer true, so the dead code goes with it.
  """
  specifiers = [
      Requirement(req).specifier
      for req in importlib.metadata.requires("adk-redis") or ()
      if Requirement(req).name == "redisvl"
  ]
  assert specifiers, "adk-redis declares no redisvl requirement"

  for specifier in specifiers:
    assert specifier.contains("0.25.1"), (
        "The declared redisvl floor no longer admits releases without"
        " create_index, so _accepts_create_index and the version branch in"
        " cache/_provider.py are dead code. Delete them and pass"
        " create_index unconditionally."
    )
