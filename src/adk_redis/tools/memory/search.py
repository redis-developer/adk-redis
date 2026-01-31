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

"""Memory search tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)


class SearchMemoryTool(BaseMemoryTool):
  """Tool for searching long-term memories.

  This tool performs semantic search against long-term memory with optional
  recency boosting. Use this when the LLM needs to recall specific information
  from past interactions.

  Example:
      ```python
      from adk_redis.tools.memory import SearchMemoryTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
          recency_boost=True,
      )
      tool = SearchMemoryTool(config=config)

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
      name: str = "search_memory",
      description: str = (
          "Searches long-term memory for relevant information. "
          "Use this to recall facts, preferences, or past interactions."
      ),
  ):
    """Initialize the Search Memory Tool.

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
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The search query for finding relevant memories",
                ),
                "limit": types.Schema(
                    type=types.Type.INTEGER,
                    description="Maximum number of memories to return (default: 10)",
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
            required=["query"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Search for relevant memories.

    Args:
        query: The search query.
        limit: Maximum number of memories to return.
        namespace: Optional namespace override.
        user_id: Optional user ID override.

    Returns:
        A dictionary with status and list of memories.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)

    query = args.get("query")
    limit = args.get("limit", self._config.search_top_k)
    self._get_namespace(args.get("namespace"))
    user_id = self._get_user_id(args.get("user_id"))

    if not query:
      return {"status": "error", "message": "query is required"}

    try:
      # Use search_memory_tool which returns a dict
      client = self._get_client()
      response = await client.search_memory_tool(
          query=query,
          max_results=limit,
          min_relevance=self._config.distance_threshold,
          user_id=user_id,
      )

      # Response is a dict with 'memories' key containing list of memory dicts
      memories_data = response.get("memories", [])
      memories = []
      for memory in memories_data:
        memories.append(
            {
                "id": memory.get("id"),
                "content": memory.get("text"),
                "score": memory.get("score", 0.0),
                "topics": memory.get("topics", []),
                "memory_type": memory.get("memory_type"),
                "created_at": memory.get("created_at"),
            }
        )

      return {
          "status": "success",
          "memories": memories,
          "count": len(memories),
      }

    except Exception as e:
      logger.error("Failed to search memories: %s", e)
      return {
          "status": "error",
          "message": f"Failed to search memories: {str(e)}",
      }
