# Copyright 2025 Google LLC
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

"""Redis Agent Memory tools for ADK.

This module provides tools for explicit LLM-controlled memory operations
with the Redis Agent Memory Server. These tools complement the automatic
memory services by allowing the LLM to directly manage long-term memories.

Available Tools:
    - MemoryPromptTool: Enrich prompts with relevant memories
    - SearchMemoryTool: Search for specific memories
    - CreateMemoryTool: Store new memories
    - DeleteMemoryTool: Delete memories by ID
    - UpdateMemoryTool: Update existing memories

Example:
    ```python
    from adk_redis.tools.memory import (
        MemoryToolConfig,
        MemoryPromptTool,
        SearchMemoryTool,
        CreateMemoryTool,
        DeleteMemoryTool,
        UpdateMemoryTool,
    )

    # Configure all tools
    config = MemoryToolConfig(
        api_base_url="http://localhost:8000",
        default_namespace="my_app",
        recency_boost=True,
    )

    # Create tools
    tools = [
        MemoryPromptTool(config=config),
        SearchMemoryTool(config=config),
        CreateMemoryTool(config=config),
        DeleteMemoryTool(config=config),
        UpdateMemoryTool(config=config),
    ]

    # Use with ADK agent
    agent = Agent(
        name="my_agent",
        tools=tools,
    )
    ```
"""

from adk_redis.tools.memory._config import MemoryToolConfig
from adk_redis.tools.memory.create import CreateMemoryTool
from adk_redis.tools.memory.delete import DeleteMemoryTool
from adk_redis.tools.memory.prompt import MemoryPromptTool
from adk_redis.tools.memory.search import SearchMemoryTool
from adk_redis.tools.memory.update import UpdateMemoryTool

__all__ = [
    "MemoryToolConfig",
    "MemoryPromptTool",
    "SearchMemoryTool",
    "CreateMemoryTool",
    "DeleteMemoryTool",
    "UpdateMemoryTool",
]

