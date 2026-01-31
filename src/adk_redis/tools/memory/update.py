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

"""Memory update tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)


class UpdateMemoryTool(BaseMemoryTool):
  """Tool for updating existing long-term memories.

  This tool allows the LLM to modify the content or metadata of existing memories.
  Use this when the user asks to update or correct previously stored information.

  Example:
      ```python
      from adk_redis.tools.memory import UpdateMemoryTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
      )
      tool = UpdateMemoryTool(config=config)

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
      name: str = "update_memory",
      description: str = (
          "Updates an existing long-term memory. "
          "Use this when the user asks to modify or correct stored information."
      ),
  ):
    """Initialize the Update Memory Tool.

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
                    description="The ID of the memory to update",
                ),
                "content": types.Schema(
                    type=types.Type.STRING,
                    description="New content for the memory",
                ),
                "topics": types.Schema(
                    type=types.Type.ARRAY,
                    description="New list of topics/tags for the memory",
                    items=types.Schema(type=types.Type.STRING),
                ),
                "namespace": types.Schema(
                    type=types.Type.STRING,
                    description="Optional namespace override",
                ),
                "user_id": types.Schema(
                    type=types.Type.STRING,
                    description="Optional user ID override",
                ),
            },
            required=["memory_id"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Update an existing long-term memory.

    Args:
        memory_id: The ID of the memory to update.
        content: New content for the memory.
        topics: New list of topics/tags.
        namespace: Optional namespace override.
        user_id: Optional user ID override.

    Returns:
        A dictionary with status and updated memory info.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)

    memory_id = args.get("memory_id")
    content = args.get("content")
    topics = args.get("topics")
    self._get_namespace(args.get("namespace"))
    self._get_user_id(args.get("user_id"))

    if not memory_id:
      return {"status": "error", "message": "memory_id is required"}

    if not content and not topics:
      return {
          "status": "error",
          "message": "At least one of content or topics must be provided",
      }

    try:
      # Build updates dict - use 'text' instead of 'content'
      updates = {}
      if content:
        updates["text"] = content
      if topics is not None:
        updates["topics"] = topics

      # edit_long_term_memory only takes memory_id and updates dict
      client = self._get_client()
      response = await client.edit_long_term_memory(
          memory_id=memory_id,
          updates=updates,
      )

      return {
          "status": "success",
          "memory_id": response.id,
          "message": f"Memory {response.id} updated successfully",
      }

    except Exception as e:
      logger.error("Failed to update memory: %s", e)
      return {
          "status": "error",
          "message": f"Failed to update memory: {str(e)}",
      }
