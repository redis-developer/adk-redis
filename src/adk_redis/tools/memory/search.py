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

from importlib import import_module
import logging
from typing import Any

from google.genai import types

from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import read_field
from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)

try:
  _agent_memory_filters_module = import_module("agent_memory_client.filters")
except ImportError:
  _Namespace: Any = None
  _UserId: Any = None
else:
  _Namespace = _agent_memory_filters_module.Namespace
  _UserId = _agent_memory_filters_module.UserId


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
        user_id: Optional user ID override. When omitted, the user is
            resolved from the ADK tool_context invocation user, then the
            configured defaults.

    Returns:
        A dictionary with status and list of memories.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)
    tool_context = kwargs.get("tool_context")

    query = args.get("query")
    limit = args.get("limit", self._config.search_top_k)
    namespace = self._get_namespace(args.get("namespace"))
    user_id = self._get_user_id(args.get("user_id"), tool_context=tool_context)

    if not query:
      return {"status": "error", "message": "query is required"}

    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        if _Namespace is None or _UserId is None:
          raise ImportError(
              "agent-memory-client package is required for memory search. "
              "Install it with: pip install adk-redis[memory]"
          )

        namespace_filter = _Namespace(eq=namespace)
        user_filter = _UserId(eq=user_id) if user_id else None
        response = (
            await (
                self._get_agent_memory_server_client().search_long_term_memory(
                    text=query,
                    namespace=namespace_filter,
                    user_id=user_filter,
                    distance_threshold=self._config.distance_threshold,
                    limit=limit,
                    recency=self._build_recency_config()
                    if self._config.recency_boost
                    else None,
                )
            )
        )

        memories = []
        for memory in response.memories:
          memories.append(
              {
                  "id": memory.id,
                  "content": memory.text,
                  "score": getattr(memory, "dist", 0.0),
                  "topics": memory.topics or [],
                  "memory_type": memory.memory_type,
                  "created_at": str(memory.created_at)
                  if memory.created_at
                  else None,
              }
          )

        return {
            "status": "success",
            "memories": memories,
            "count": len(memories),
        }

      filters: dict[str, Any] = {"namespace": {"eq": namespace}}
      if user_id:
        filters["ownerId"] = {"eq": user_id}
      request: dict[str, Any] = {
          "text": query,
          "limit": limit,
          "filter": filters,
          "filterOp": "all",
      }
      if self._config.distance_threshold is not None:
        request["similarityThreshold"] = self._config.distance_threshold

      async with self._agent_memory() as agent_memory:
        response = await agent_memory.search_long_term_memory_async(
            request=request
        )

      memories = []
      for memory in read_field(response, "items", []) or []:
        memory_type = read_field(memory, "memory_type")
        created_at = read_field(memory, "created_at")
        memories.append(
            {
                "id": read_field(memory, "id"),
                "content": read_field(memory, "text"),
                "score": read_field(memory, "score", 0.0),
                "topics": read_field(memory, "topics", []) or [],
                "memory_type": str(getattr(memory_type, "value", memory_type))
                if memory_type
                else None,
                "created_at": str(created_at) if created_at else None,
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
