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

"""Memory prompt enrichment tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import read_field
from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger(__name__)


class MemoryPromptTool(BaseMemoryTool):
  """Tool for enriching prompts with relevant memories.

  This tool searches long-term memory for relevant context and enriches
  a system prompt with the retrieved memories. It's useful for providing
  the LLM with personalized context based on past interactions.

  Example:
      ```python
      from adk_redis.tools.memory import MemoryPromptTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
      )
      tool = MemoryPromptTool(config=config)

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
      name: str = "memory_prompt",
      description: str = (
          "Enriches a prompt with relevant memories from long-term storage. "
          "Use this to provide personalized context based on past interactions."
      ),
  ):
    """Initialize the Memory Prompt Tool.

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
                    description="The query to search for relevant memories",
                ),
                "system_prompt": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Optional base system prompt to enrich with memories"
                    ),
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
    """Enrich a prompt with relevant memories.

    Args:
        query: The query to search for relevant memories.
        system_prompt: Optional base system prompt to enrich.
        namespace: Optional namespace override.
        user_id: Optional user ID override. When omitted, the user is
            resolved from the ADK tool_context invocation user, then the
            configured defaults.

    Returns:
        A dictionary with status and enriched_prompt.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)
    tool_context = kwargs.get("tool_context")

    query = args.get("query")
    system_prompt = args.get("system_prompt", "")
    namespace = self._get_namespace(args.get("namespace"))
    user_id = self._get_user_id(args.get("user_id"), tool_context=tool_context)

    if not query:
      return {"status": "error", "message": "query is required"}

    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        response = await self._get_agent_memory_server_client().memory_prompt(
            query=query,
            user_id=user_id,
            namespace=namespace,
            long_term_search={"limit": self._config.search_top_k},
        )
        enriched_prompt = response.get("prompt", query)
        if system_prompt:
          enriched_prompt = f"{system_prompt}\n\n{enriched_prompt}"

        return {
            "status": "success",
            "enriched_prompt": enriched_prompt,
            "memories_used": len(response.get("memories", [])),
        }

      filters: dict[str, Any] = {"namespace": {"eq": namespace}}
      if user_id:
        filters["ownerId"] = {"eq": user_id}
      request = {
          "text": query,
          "limit": self._config.search_top_k,
          "filter": filters,
          "filterOp": "all",
      }

      async with self._agent_memory() as agent_memory:
        response = await agent_memory.search_long_term_memory_async(
            request=request
        )

      memory_lines = [
          f"- {read_field(memory, 'text')}"
          for memory in read_field(response, "items", []) or []
          if read_field(memory, "text")
      ]
      if memory_lines:
        memory_context = "\n".join(memory_lines)
        enriched_prompt = (
            "Relevant long-term memories:\n"
            f"{memory_context}\n\nCurrent query:\n{query}"
        )
      else:
        enriched_prompt = query

      if system_prompt:
        enriched_prompt = f"{system_prompt}\n\n{enriched_prompt}"

      memories_used = len(memory_lines)

      return {
          "status": "success",
          "enriched_prompt": enriched_prompt,
          "memories_used": memories_used,
      }

    except Exception as e:
      logger.error("Failed to enrich prompt: %s", e)
      return {
          "status": "error",
          "message": f"Failed to enrich prompt: {str(e)}",
      }
