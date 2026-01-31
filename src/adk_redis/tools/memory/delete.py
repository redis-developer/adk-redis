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

"""Memory deletion tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)


class DeleteMemoryTool(BaseMemoryTool):
  """Tool for deleting long-term memories.

  This tool allows the LLM to delete specific memories by ID.
  Use this when the user asks to forget something.

  Example:
      ```python
      from adk_redis.tools.memory import DeleteMemoryTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
      )
      tool = DeleteMemoryTool(config=config)

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
      name: str = "delete_memory",
      description: str = (
          "Deletes one or more long-term memories by ID. "
          "Use this when the user asks you to forget something."
      ),
  ):
    """Initialize the Delete Memory Tool.

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
                "memory_ids": types.Schema(
                    type=types.Type.ARRAY,
                    description="List of memory IDs to delete",
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
            required=["memory_ids"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Delete long-term memories by ID.

    Args:
        memory_ids: List of memory IDs to delete.
        namespace: Optional namespace override.
        user_id: Optional user ID override.

    Returns:
        A dictionary with status and deleted_count.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)

    memory_ids = args.get("memory_ids", [])
    self._get_namespace(args.get("namespace"))
    self._get_user_id(args.get("user_id"))

    if not memory_ids:
      return {"status": "error", "message": "memory_ids is required"}

    try:
      # delete_long_term_memories only takes memory_ids
      client = self._get_client()
      response = await client.delete_long_term_memories(
          memory_ids=memory_ids,
      )

      # Response is AckResponse with 'status' field containing message like "ok, deleted 2 memories"
      status_msg = response.status

      # Parse the deleted count from the status message
      import re

      match = re.search(r"deleted (\d+)", status_msg)
      deleted_count = int(match.group(1)) if match else 0

      is_success = "ok" in status_msg.lower()

      return {
          "status": "success" if is_success else "error",
          "deleted_count": deleted_count,
          "message": status_msg,
      }

    except Exception as e:
      logger.error("Failed to delete memories: %s", e)
      return {
          "status": "error",
          "message": f"Failed to delete memories: {str(e)}",
      }
