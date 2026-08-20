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

"""Memory retrieval tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import read_field
from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger(__name__)


class GetMemoryTool(BaseMemoryTool):
  """Tool for retrieving a specific long-term memory by ID.

  This tool allows the LLM to retrieve a specific memory when it knows
  the memory ID. Use this when you need to access the full details of
  a memory that was previously found via search.

  Example:
      ```python
      from adk_redis.tools.memory import GetMemoryTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
      )
      tool = GetMemoryTool(config=config)

      # Use with ADK agent
      agent = Agent(
          name="my_agent",
          tools=[tool],
      )
      ```
  """

  def __init__(
      self,
      *,
      config: MemoryToolConfig | None = None,
      name: str = "get_memory",
      description: str = (
          "Retrieves a specific long-term memory by its ID. "
          "Use this when you need the full details of a known memory."
      ),
  ):
    """Initialize the Get Memory Tool.

    Args:
        config: Configuration for the tool. If None, uses defaults.
        name: The name of the tool (exposed to LLM).
        description: The description of the tool (exposed to LLM).
    """
    super().__init__(
        config=config or MemoryToolConfig(),
        name=name,
        description=description,
    )

  def _get_declaration(self) -> types.FunctionDeclaration:
    """Get the tool declaration for the LLM."""
    return types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "memory_id": types.Schema(
                    type=types.Type.STRING,
                    description="The unique ID of the memory to retrieve",
                ),
            },
            required=["memory_id"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Retrieve a specific memory by ID.

    Args:
        memory_id: The unique ID of the memory to retrieve.

    Returns:
        A dictionary with status and memory details.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)

    memory_id = args.get("memory_id")

    if not memory_id:
      return {"status": "error", "message": "memory_id is required"}

    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        memory = (
            await (
                self._get_agent_memory_server_client().get_long_term_memory(
                    memory_id=memory_id
                )
            )
        )

        return {
            "status": "success",
            "memory": {
                "id": memory.id,
                "content": memory.text,
                "topics": memory.topics or [],
                "entities": memory.entities or [],
                "memory_type": memory.memory_type,
                "namespace": memory.namespace,
                "user_id": memory.user_id,
                "session_id": memory.session_id,
                "created_at": str(memory.created_at)
                if memory.created_at
                else None,
                "last_accessed": str(memory.last_accessed)
                if memory.last_accessed
                else None,
            },
        }

      async with self._agent_memory() as agent_memory:
        memory = await agent_memory.get_long_term_memory_async(
            memory_id=memory_id
        )
      memory_type = read_field(memory, "memory_type")
      created_at = read_field(memory, "created_at")
      updated_at = read_field(memory, "updated_at")

      return {
          "status": "success",
          "memory": {
              "id": read_field(memory, "id"),
              "content": read_field(memory, "text"),
              "topics": read_field(memory, "topics", []) or [],
              "memory_type": str(getattr(memory_type, "value", memory_type))
              if memory_type
              else None,
              "namespace": read_field(memory, "namespace"),
              "user_id": read_field(memory, "owner_id"),
              "session_id": read_field(memory, "session_id"),
              "created_at": str(created_at) if created_at else None,
              "updated_at": str(updated_at) if updated_at else None,
          },
      }

    except Exception as e:
      error_msg = str(e)
      if "not found" in error_msg.lower() or "404" in error_msg:
        return {
            "status": "error",
            "message": f"Memory with ID '{memory_id}' not found",
        }
      logger.error("Failed to get memory: %s", e)
      return {
          "status": "error",
          "message": f"Failed to get memory: {error_msg}",
      }
