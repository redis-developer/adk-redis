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

"""ADK-Redis: Redis integrations for Google's Agent Development Kit (ADK).

This package provides Redis-backed implementations of ADK services:

Memory Services:
    - RedisLongTermMemoryService: Long-term memory with semantic search

Session Services:
    - RedisWorkingMemorySessionService: Session management with working memory

Search Tools:
    - RedisVectorSearchTool: Vector similarity search
    - RedisHybridSearchTool: Combined vector + BM25 search
    - RedisRangeSearchTool: Distance threshold search
    - RedisTextSearchTool: Full-text BM25 search

Memory Tools:
    - MemoryPromptTool: Enrich prompts with relevant memories
    - SearchMemoryTool: Search long-term memories
    - CreateMemoryTool: Store new memories
    - DeleteMemoryTool: Delete memories by ID
    - UpdateMemoryTool: Update existing memories

Example:
    ```python
    from adk_redis import (
        RedisLongTermMemoryService,
        RedisLongTermMemoryServiceConfig,
        RedisWorkingMemorySessionService,
        RedisWorkingMemorySessionServiceConfig,
    )

    # Configure memory service
    memory_config = RedisLongTermMemoryServiceConfig(
        api_base_url="http://localhost:8000",
    )
    memory_service = RedisLongTermMemoryService(config=memory_config)

    # Configure session service
    session_config = RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://localhost:8000",
    )
    session_service = RedisWorkingMemorySessionService(config=session_config)
    ```
"""

from adk_redis._version import __version__
# Memory services
from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig
# Session services
from adk_redis.sessions import RedisWorkingMemorySessionService
from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig
# Search tools - import from tools submodule
from adk_redis.tools import BaseRedisSearchTool
from adk_redis.tools import RedisAggregatedHybridQueryConfig
from adk_redis.tools import RedisHybridQueryConfig
from adk_redis.tools import RedisHybridSearchTool
from adk_redis.tools import RedisRangeQueryConfig
from adk_redis.tools import RedisRangeSearchTool
from adk_redis.tools import RedisTextQueryConfig
from adk_redis.tools import RedisTextSearchTool
from adk_redis.tools import RedisVectorQueryConfig
from adk_redis.tools import RedisVectorSearchTool
from adk_redis.tools import VectorizedSearchTool
# Memory tools
from adk_redis.tools import CreateMemoryTool
from adk_redis.tools import DeleteMemoryTool
from adk_redis.tools import MemoryPromptTool
from adk_redis.tools import MemoryToolConfig
from adk_redis.tools import SearchMemoryTool
from adk_redis.tools import UpdateMemoryTool

__all__ = [
    # Version
    "__version__",
    # Memory services
    "RedisLongTermMemoryService",
    "RedisLongTermMemoryServiceConfig",
    # Session services
    "RedisWorkingMemorySessionService",
    "RedisWorkingMemorySessionServiceConfig",
    # Search tools - base classes
    "BaseRedisSearchTool",
    "VectorizedSearchTool",
    # Search tools - implementations
    "RedisVectorSearchTool",
    "RedisHybridSearchTool",
    "RedisRangeSearchTool",
    "RedisTextSearchTool",
    # Search tools - config classes
    "RedisVectorQueryConfig",
    "RedisHybridQueryConfig",
    "RedisAggregatedHybridQueryConfig",
    "RedisRangeQueryConfig",
    "RedisTextQueryConfig",
    # Memory tools
    "MemoryPromptTool",
    "SearchMemoryTool",
    "CreateMemoryTool",
    "DeleteMemoryTool",
    "UpdateMemoryTool",
    "MemoryToolConfig",
]
