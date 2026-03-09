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

"""MCP-based memory tools for ADK using Agent Memory Server.

This module provides helper functions to create MCP toolsets that connect
to the Agent Memory Server's MCP endpoint. This is an alternative to the
REST-based tools in `adk_redis.tools.memory`.

The Agent Memory Server exposes these MCP tools:
    - search_long_term_memory: Search for relevant memories
    - get_long_term_memory: Retrieve a specific memory by ID
    - create_long_term_memories: Store new memories
    - edit_long_term_memory: Update existing memories
    - delete_long_term_memories: Delete memories by ID
    - memory_prompt: Hydrate prompts with memory context
    - set_working_memory: Update working memory data

Example:
    ```python
    from google.adk import Agent
    from adk_redis.tools.mcp_memory import create_memory_mcp_toolset

    # Create MCP toolset for Agent Memory Server
    memory_tools = create_memory_mcp_toolset(
        server_url="http://localhost:8000",
        tool_filter=["search_long_term_memory", "create_long_term_memories"],
    )

    agent = Agent(
        model="gemini-2.0-flash",
        name="memory_agent",
        instruction="You have access to long-term memory.",
        tools=[memory_tools],
    )
    ```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from google.adk.tools.mcp_tool import McpToolset


def create_memory_mcp_toolset(
    server_url: str = "http://localhost:8000",
    tool_filter: list[str] | None = None,
) -> "McpToolset":
  """Create an MCP toolset for Agent Memory Server.

  This function creates an McpToolset configured to connect to the
  Agent Memory Server's SSE endpoint. The toolset provides access to
  all memory operations via the Model Context Protocol.

  Args:
      server_url: Base URL of the Agent Memory Server (without /sse suffix).
          Default: "http://localhost:8000"
      tool_filter: Optional list of tool names to expose. If None, all
          available tools are exposed. Available tools:
          - search_long_term_memory
          - get_long_term_memory
          - create_long_term_memories
          - edit_long_term_memory
          - delete_long_term_memories
          - memory_prompt
          - set_working_memory

  Returns:
      McpToolset configured for Agent Memory Server.

  Raises:
      ImportError: If google-adk is not installed with MCP support.

  Example:
      ```python
      from google.adk import Agent
      from adk_redis.tools.mcp_memory import create_memory_mcp_toolset

      # All memory tools
      all_tools = create_memory_mcp_toolset(
          server_url="http://localhost:8000",
      )

      # Only search and create tools
      limited_tools = create_memory_mcp_toolset(
          server_url="http://localhost:8000",
          tool_filter=["search_long_term_memory", "create_long_term_memories"],
      )

      agent = Agent(
          model="gemini-2.0-flash",
          name="memory_agent",
          tools=[limited_tools],
      )
      ```
  """
  try:
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        SseConnectionParams,
    )
  except ImportError as e:
    raise ImportError(
        "google-adk with MCP support is required. "
        "Install it with: pip install google-adk[mcp]"
    ) from e

  # Ensure URL doesn't have trailing slash and add /sse endpoint
  base_url = server_url.rstrip("/")
  sse_url = f"{base_url}/sse"

  return McpToolset(
      connection_params=SseConnectionParams(url=sse_url),
      tool_filter=tool_filter,
  )


# Available MCP tool names for reference
MCP_TOOL_SEARCH = "search_long_term_memory"
MCP_TOOL_GET = "get_long_term_memory"
MCP_TOOL_CREATE = "create_long_term_memories"
MCP_TOOL_EDIT = "edit_long_term_memory"
MCP_TOOL_DELETE = "delete_long_term_memories"
MCP_TOOL_PROMPT = "memory_prompt"
MCP_TOOL_SET_WORKING_MEMORY = "set_working_memory"

ALL_MCP_TOOLS = [
    MCP_TOOL_SEARCH,
    MCP_TOOL_GET,
    MCP_TOOL_CREATE,
    MCP_TOOL_EDIT,
    MCP_TOOL_DELETE,
    MCP_TOOL_PROMPT,
    MCP_TOOL_SET_WORKING_MEMORY,
]

__all__ = [
    "create_memory_mcp_toolset",
    "MCP_TOOL_SEARCH",
    "MCP_TOOL_GET",
    "MCP_TOOL_CREATE",
    "MCP_TOOL_EDIT",
    "MCP_TOOL_DELETE",
    "MCP_TOOL_PROMPT",
    "MCP_TOOL_SET_WORKING_MEMORY",
    "ALL_MCP_TOOLS",
]
