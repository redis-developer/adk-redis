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

"""Tests for package imports."""

import importlib
import sys
import warnings

import pytest


class TestMemoryImports:
  """Test memory module imports."""

  def test_memory_service_import(self):
    """Test RedisLongTermMemoryService can be imported."""
    from adk_redis import RedisLongTermMemoryService

    assert RedisLongTermMemoryService is not None

  def test_memory_config_import(self):
    """Test RedisLongTermMemoryServiceConfig can be imported."""
    from adk_redis import RedisLongTermMemoryServiceConfig

    assert RedisLongTermMemoryServiceConfig is not None

  def test_memory_submodule_import(self):
    """Test memory submodule imports."""
    from adk_redis.memory import RedisLongTermMemoryService
    from adk_redis.memory import RedisLongTermMemoryServiceConfig

    assert RedisLongTermMemoryService is not None
    assert RedisLongTermMemoryServiceConfig is not None


class TestSessionImports:
  """Test session module imports."""

  def test_session_service_import(self):
    """Test RedisSessionMemoryService can be imported."""
    from adk_redis import RedisSessionMemoryService

    assert RedisSessionMemoryService is not None

  def test_session_config_import(self):
    """Test RedisSessionMemoryServiceConfig can be imported."""
    from adk_redis import RedisSessionMemoryServiceConfig

    assert RedisSessionMemoryServiceConfig is not None

  def test_session_submodule_import(self):
    """Test sessions submodule imports."""
    from adk_redis.sessions import RedisSessionMemoryService
    from adk_redis.sessions import RedisSessionMemoryServiceConfig

    assert RedisSessionMemoryService is not None
    assert RedisSessionMemoryServiceConfig is not None

  def test_deprecated_session_aliases(self):
    """Deprecated aliases still import and subclass the new names."""
    from adk_redis import RedisSessionMemoryService
    from adk_redis import RedisSessionMemoryServiceConfig
    from adk_redis import RedisWorkingMemorySessionService
    from adk_redis import RedisWorkingMemorySessionServiceConfig

    assert issubclass(
        RedisWorkingMemorySessionService, RedisSessionMemoryService
    )
    assert issubclass(
        RedisWorkingMemorySessionServiceConfig, RedisSessionMemoryServiceConfig
    )

    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")
      RedisWorkingMemorySessionService()
      RedisWorkingMemorySessionServiceConfig()

    categories = [w.category for w in caught]
    assert categories.count(DeprecationWarning) == 2

  def test_deprecated_session_module_path(self):
    """Legacy module path still imports and warns until 0.1.0."""
    sys.modules.pop("adk_redis.sessions.working_memory", None)
    with warnings.catch_warnings(record=True) as caught:
      warnings.simplefilter("always")
      working_memory = importlib.import_module(
          "adk_redis.sessions.working_memory"
      )

    assert working_memory.RedisWorkingMemorySessionService is not None
    assert working_memory.RedisSessionMemoryService is not None
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


class TestToolImports:
  """Test tools module imports."""

  @pytest.mark.skipif(
      not pytest.importorskip("redisvl", reason="redisvl not installed"),
      reason="redisvl not installed",
  )
  def test_vector_search_tool_import(self):
    """Test RedisVectorSearchTool can be imported."""
    from adk_redis import RedisVectorSearchTool

    assert RedisVectorSearchTool is not None

  @pytest.mark.skipif(
      not pytest.importorskip("redisvl", reason="redisvl not installed"),
      reason="redisvl not installed",
  )
  def test_hybrid_search_tool_import(self):
    """Test RedisHybridSearchTool can be imported."""
    from adk_redis import RedisHybridSearchTool

    assert RedisHybridSearchTool is not None

  @pytest.mark.skipif(
      not pytest.importorskip("redisvl", reason="redisvl not installed"),
      reason="redisvl not installed",
  )
  def test_range_search_tool_import(self):
    """Test RedisRangeSearchTool can be imported."""
    from adk_redis import RedisRangeSearchTool

    assert RedisRangeSearchTool is not None

  @pytest.mark.skipif(
      not pytest.importorskip("redisvl", reason="redisvl not installed"),
      reason="redisvl not installed",
  )
  def test_text_search_tool_import(self):
    """Test RedisTextSearchTool can be imported."""
    from adk_redis import RedisTextSearchTool

    assert RedisTextSearchTool is not None

  @pytest.mark.skipif(
      not pytest.importorskip("redisvl", reason="redisvl not installed"),
      reason="redisvl not installed",
  )
  def test_config_imports(self):
    """Test config classes can be imported."""
    from adk_redis import RedisAggregatedHybridQueryConfig
    from adk_redis import RedisHybridQueryConfig
    from adk_redis import RedisRangeQueryConfig
    from adk_redis import RedisTextQueryConfig
    from adk_redis import RedisVectorQueryConfig

    assert RedisVectorQueryConfig is not None
    assert RedisHybridQueryConfig is not None
    assert RedisAggregatedHybridQueryConfig is not None
    assert RedisRangeQueryConfig is not None
    assert RedisTextQueryConfig is not None


class TestMemoryToolImports:
  """Test memory tool imports."""

  def test_memory_tool_config_import(self):
    """Test MemoryToolConfig can be imported."""
    from adk_redis import MemoryToolConfig

    assert MemoryToolConfig is not None

  def test_search_memory_tool_import(self):
    """Test SearchMemoryTool can be imported."""
    from adk_redis import SearchMemoryTool

    assert SearchMemoryTool is not None

  def test_get_memory_tool_import(self):
    """Test GetMemoryTool can be imported."""
    from adk_redis import GetMemoryTool

    assert GetMemoryTool is not None

  def test_create_memory_tool_import(self):
    """Test CreateMemoryTool can be imported."""
    from adk_redis import CreateMemoryTool

    assert CreateMemoryTool is not None

  def test_update_memory_tool_import(self):
    """Test UpdateMemoryTool can be imported."""
    from adk_redis import UpdateMemoryTool

    assert UpdateMemoryTool is not None

  def test_delete_memory_tool_import(self):
    """Test DeleteMemoryTool can be imported."""
    from adk_redis import DeleteMemoryTool

    assert DeleteMemoryTool is not None

  def test_memory_prompt_tool_import(self):
    """Test MemoryPromptTool can be imported."""
    from adk_redis import MemoryPromptTool

    assert MemoryPromptTool is not None

  def test_memory_tools_submodule_import(self):
    """Test memory tools submodule imports."""
    from adk_redis.tools.memory import CreateMemoryTool
    from adk_redis.tools.memory import DeleteMemoryTool
    from adk_redis.tools.memory import GetMemoryTool
    from adk_redis.tools.memory import MemoryPromptTool
    from adk_redis.tools.memory import MemoryToolConfig
    from adk_redis.tools.memory import SearchMemoryTool
    from adk_redis.tools.memory import UpdateMemoryTool

    assert MemoryToolConfig is not None
    assert MemoryPromptTool is not None
    assert SearchMemoryTool is not None
    assert GetMemoryTool is not None
    assert CreateMemoryTool is not None
    assert UpdateMemoryTool is not None
    assert DeleteMemoryTool is not None


class TestCacheImports:
  """Test cache module imports."""

  def test_base_cache_provider_import(self):
    """Test BaseCacheProvider can be imported."""
    from adk_redis import BaseCacheProvider

    assert BaseCacheProvider is not None

  def test_cache_entry_import(self):
    """Test CacheEntry can be imported."""
    from adk_redis import CacheEntry

    assert CacheEntry is not None

  def test_langcache_provider_import(self):
    """Test LangCacheProvider can be imported."""
    from adk_redis import LangCacheProvider

    assert LangCacheProvider is not None

  def test_langcache_provider_config_import(self):
    """Test LangCacheProviderConfig can be imported."""
    from adk_redis import LangCacheProviderConfig

    assert LangCacheProviderConfig is not None

  def test_redisvl_cache_provider_import(self):
    """Test RedisVLCacheProvider can be imported."""
    from adk_redis import RedisVLCacheProvider

    assert RedisVLCacheProvider is not None

  def test_cache_submodule_import(self):
    """Test cache submodule imports work."""
    from adk_redis.cache import LangCacheProvider
    from adk_redis.cache import LangCacheProviderConfig

    assert LangCacheProvider is not None
    assert LangCacheProviderConfig is not None
