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
    """Test RedisWorkingMemorySessionService can be imported."""
    from adk_redis import RedisWorkingMemorySessionService

    assert RedisWorkingMemorySessionService is not None

  def test_session_config_import(self):
    """Test RedisWorkingMemorySessionServiceConfig can be imported."""
    from adk_redis import RedisWorkingMemorySessionServiceConfig

    assert RedisWorkingMemorySessionServiceConfig is not None

  def test_session_submodule_import(self):
    """Test sessions submodule imports."""
    from adk_redis.sessions import RedisWorkingMemorySessionService
    from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig

    assert RedisWorkingMemorySessionService is not None
    assert RedisWorkingMemorySessionServiceConfig is not None


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


class TestMCPToolImports:
  """Test MCP tool imports."""

  def test_create_memory_mcp_toolset_import(self):
    """Test create_memory_mcp_toolset can be imported."""
    from adk_redis import create_memory_mcp_toolset

    assert create_memory_mcp_toolset is not None

  def test_all_mcp_tools_import(self):
    """Test ALL_MCP_TOOLS can be imported."""
    from adk_redis import ALL_MCP_TOOLS

    assert ALL_MCP_TOOLS is not None
    assert isinstance(ALL_MCP_TOOLS, list)
    assert len(ALL_MCP_TOOLS) == 7

  def test_mcp_memory_submodule_import(self):
    """Test mcp_memory submodule imports."""
    from adk_redis.tools.mcp_memory import ALL_MCP_TOOLS
    from adk_redis.tools.mcp_memory import create_memory_mcp_toolset
    from adk_redis.tools.mcp_memory import MCP_TOOL_CREATE
    from adk_redis.tools.mcp_memory import MCP_TOOL_DELETE
    from adk_redis.tools.mcp_memory import MCP_TOOL_EDIT
    from adk_redis.tools.mcp_memory import MCP_TOOL_GET
    from adk_redis.tools.mcp_memory import MCP_TOOL_PROMPT
    from adk_redis.tools.mcp_memory import MCP_TOOL_SEARCH
    from adk_redis.tools.mcp_memory import MCP_TOOL_SET_WORKING_MEMORY

    assert create_memory_mcp_toolset is not None
    assert ALL_MCP_TOOLS is not None
    assert MCP_TOOL_SEARCH == "search_long_term_memory"
    assert MCP_TOOL_GET == "get_long_term_memory"
    assert MCP_TOOL_CREATE == "create_long_term_memories"
    assert MCP_TOOL_EDIT == "edit_long_term_memory"
    assert MCP_TOOL_DELETE == "delete_long_term_memories"
    assert MCP_TOOL_PROMPT == "memory_prompt"
    assert MCP_TOOL_SET_WORKING_MEMORY == "set_working_memory"


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

  def test_langcache_cache_provider_import(self):
    """Test LangCacheCacheProvider can be imported."""
    from adk_redis import LangCacheCacheProvider

    assert LangCacheCacheProvider is not None

  def test_langcache_cache_provider_config_import(self):
    """Test LangCacheCacheProviderConfig can be imported."""
    from adk_redis import LangCacheCacheProviderConfig

    assert LangCacheCacheProviderConfig is not None

  def test_redisvl_cache_provider_import(self):
    """Test RedisVLCacheProvider can be imported."""
    from adk_redis import RedisVLCacheProvider

    assert RedisVLCacheProvider is not None

  def test_cache_submodule_import(self):
    """Test cache submodule imports work."""
    from adk_redis.cache import LangCacheCacheProvider
    from adk_redis.cache import LangCacheCacheProviderConfig

    assert LangCacheCacheProvider is not None
    assert LangCacheCacheProviderConfig is not None