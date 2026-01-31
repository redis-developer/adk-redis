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
