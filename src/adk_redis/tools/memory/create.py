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

"""Memory creation tool for Redis Agent Memory Server."""

from __future__ import annotations

import logging
from typing import Any
import uuid

from google.genai import types

from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import read_field
from adk_redis.memory._utils import stable_memory_id
from adk_redis.tools.memory._base import BaseMemoryTool
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)


class CreateMemoryTool(BaseMemoryTool):
  """Tool for creating new long-term memories.

  This tool allows the LLM to explicitly store information in long-term memory.
  Use this when the user asks to remember something specific.

  Example:
      ```python
      from adk_redis.tools.memory import CreateMemoryTool, MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
      )
      tool = CreateMemoryTool(config=config)

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
      name: str = "create_memory",
      description: str = (
          "Creates a new long-term memory. "
          "Use this when the user asks you to remember something."
      ),
  ):
    """Initialize the Create Memory Tool.

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
                "content": types.Schema(
                    type=types.Type.STRING,
                    description="The content of the memory to store",
                ),
                "topics": types.Schema(
                    type=types.Type.ARRAY,
                    description="Optional list of topics/tags for the memory",
                    items=types.Schema(type=types.Type.STRING),
                ),
                "memory_type": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "Type of memory: 'semantic' (facts/preferences), "
                        "'episodic' (events/experiences), or 'message' (conversation)"
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
            required=["content"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Create a new long-term memory.

    Args:
        content: The content of the memory to store.
        topics: Optional list of topics/tags.
        memory_type: Type of memory (semantic, episodic, message).
        namespace: Optional namespace override.
        user_id: Optional user ID override. When omitted, the user is
            resolved from the ADK tool_context invocation user, then the
            configured defaults.
        id: Optional client-supplied memory ID for idempotent retries.
            This is an application-level parameter and is intentionally
            not exposed in the LLM tool declaration; direct callers pass
            it via ``run_async(id=..., content=...)`` or
            ``run_async(args={"id": ..., ...})``. On the managed Redis
            Agent Memory backend the ID and resolved namespace/user scope
            are mapped to a collision-resistant record ID, so retrying with
            the same ID in the same scope upserts instead of creating a
            duplicate. The self-hosted
            opensource-agent-memory backend cannot honor client IDs; a
            warning is logged and the write proceeds with a
            server-generated ID.

    Returns:
        A dictionary with status and memory_id.
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)
    tool_context = kwargs.get("tool_context")

    content = args.get("content")
    topics = args.get("topics", [])
    memory_type_raw = args.get("memory_type", "semantic")
    namespace = self._get_namespace(args.get("namespace"))
    user_id = self._get_user_id(args.get("user_id"), tool_context=tool_context)
    client_memory_id = args.get("id")

    if not content:
      return {"status": "error", "message": "content is required"}

    # Map invalid memory types to valid ones
    # Valid types: 'semantic', 'episodic', 'message'
    memory_type_map = {
        "preference": "semantic",
        "fact": "semantic",
        "event": "episodic",
        "experience": "episodic",
        "conversation": "message",
    }
    memory_type = memory_type_map.get(memory_type_raw, memory_type_raw)
    if memory_type not in ("semantic", "episodic", "message"):
      memory_type = "semantic"  # Default fallback

    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        if client_memory_id is not None:
          logger.warning(
              "A client-supplied memory id is not supported by the "
              "opensource-agent-memory backend: add_memory_tool generates "
              "its own memory ID. Proceeding without the client id."
          )
        session_id = f"standalone_{uuid.uuid4().hex[:8]}"
        response = await self._get_agent_memory_server_client().add_memory_tool(
            session_id=session_id,
            text=content,
            memory_type=memory_type,
            topics=topics if topics else None,
            namespace=namespace,
            user_id=user_id,
        )

        if response.get("success"):
          return {
              "status": "success",
              "memory_id": response.get("memory_id", session_id),
              "message": response.get(
                  "summary",
                  "Memory created successfully",
              ),
          }
        return {
            "status": "error",
            "message": response.get("summary", "Failed to create memory"),
        }

      if client_memory_id is not None:
        raw_client_memory_id = str(client_memory_id)
        if not raw_client_memory_id.strip():
          raise ValueError("Client-supplied memory id must not be empty")
        memory_id = stable_memory_id(
            "client",
            namespace,
            user_id or "",
            raw_client_memory_id,
        )
      else:
        memory_id = stable_memory_id(
            "tool",
            namespace,
            user_id or "",
            memory_type,
            content,
        )
      record = {
          "id": memory_id,
          "text": content,
          "ownerId": user_id,
          "namespace": namespace,
          "topics": topics if topics else None,
          "memoryType": memory_type,
      }

      async with self._agent_memory() as agent_memory:
        response = await agent_memory.bulk_create_long_term_memories_async(
            memories=[record]
        )

      errors = read_field(response, "errors")
      if errors:
        return {
            "status": "error",
            "message": f"Failed to create memory: {errors}",
        }

      created = read_field(response, "created", []) or [memory_id]
      return {
          "status": "success",
          "memory_id": created[0],
          "message": "Memory created successfully",
      }

    except Exception as e:
      logger.error("Failed to create memory: %s", e)
      return {
          "status": "error",
          "message": f"Failed to create memory: {str(e)}",
      }
