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

"""Memory agent over the langcache (Redis Agent Memory) MCP server.

Unlike examples/fitness_coach_mcp (which connects to the open-source Agent
Memory Server via SSE), this agent connects to the langcache memory-dataplane
MCP server, which speaks streamable HTTP and is multi-tenant: every endpoint is
scoped to a store at /v1/stores/{storeId}/mcp and authenticated with that
store's Bearer token.
"""

import os

from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)

# Full MCP endpoint including the store path, e.g.
#   http://localhost:9100/v1/stores/my-store/mcp
LANGCACHE_MCP_URL = os.getenv(
    "LANGCACHE_MCP_URL", "http://localhost:9100/v1/stores/test-store/mcp"
)
# The per-store API key, sent in X-API-Key (cloud-context-engine convention).
# Omit only for an auth-disabled / local server.
LANGCACHE_MCP_TOKEN = os.getenv("LANGCACHE_MCP_TOKEN")
# Optional IdP bearer JWT, sent in Authorization when the store has an IdP.
LANGCACHE_MCP_JWT = os.getenv("LANGCACHE_MCP_JWT")


def _mcp_headers() -> dict[str, str] | None:
  headers: dict[str, str] = {}
  if LANGCACHE_MCP_TOKEN:
    headers["X-API-Key"] = LANGCACHE_MCP_TOKEN
  if LANGCACHE_MCP_JWT:
    headers["Authorization"] = f"Bearer {LANGCACHE_MCP_JWT}"
  return headers or None


_headers = _mcp_headers()

memory_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=LANGCACHE_MCP_URL,
        headers=_headers,
    ),
    tool_filter=[
        "search_long_term_memory",
        "create_long_term_memories",
        "get_long_term_memory",
    ],
)

SYSTEM_PROMPT = """You are a helpful assistant with persistent long-term memory
backed by Redis Agent Memory (langcache).

- At the START of a conversation, call search_long_term_memory to load what you
  already know about the user (filter by their owner_id).
- When the user shares durable facts or preferences, store them with
  create_long_term_memories as `semantic` memories, including a stable `id`,
  the user's `owner_id`, and relevant `topics`.
- Be transparent about what you remember, and never invent facts you did not
  retrieve from memory.
"""

root_agent = Agent(
    model="gemini-2.5-flash",
    name="langcache_memory_agent",
    description="Assistant with persistent memory via the langcache MCP server",
    tools=[memory_tools],
    instruction=SYSTEM_PROMPT,
)
