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

"""End-to-end interop test against the langcache memory-dataplane MCP server.

The langcache "Redis Agent Memory" data plane exposes its memory tools over the
Model Context Protocol (streamable HTTP) at /v1/stores/{storeId}/mcp. This test
verifies two things:

1. ADK's native ``McpToolset`` can discover the langcache tool surface — i.e.
   adk-redis agents can use langcache memory over MCP exactly as they use the
   open-source Agent Memory Server (see examples/fitness_coach_mcp).
2. The tools work over the wire for a create -> get -> search round trip.

Gated on ``LANGCACHE_MCP_URL`` (point it at a running endpoint), e.g.::

    LANGCACHE_MCP_URL=http://localhost:9100/v1/stores/test-store/mcp \
        uv run pytest tests/integration/test_langcache_mcp_end_to_end.py

If the endpoint enforces auth, also set ``LANGCACHE_MCP_TOKEN`` (sent as a
Bearer token).
"""

from __future__ import annotations

import os
import uuid

import pytest

LANGCACHE_MCP_URL = os.environ.get("LANGCACHE_MCP_URL")
# The per-store API key, sent in X-API-Key (cloud-context-engine convention).
LANGCACHE_MCP_TOKEN = os.environ.get("LANGCACHE_MCP_TOKEN")
# Optional IdP bearer JWT, sent in Authorization when the store has an IdP.
LANGCACHE_MCP_JWT = os.environ.get("LANGCACHE_MCP_JWT")

REQUIRES_LANGCACHE_MCP = pytest.mark.skipif(
    not LANGCACHE_MCP_URL,
    reason=(
        "LANGCACHE_MCP_URL not set. Point it at a running memory-dataplane MCP "
        "endpoint, e.g. http://localhost:9100/v1/stores/test-store/mcp"
    ),
)

pytestmark = REQUIRES_LANGCACHE_MCP

# The full Phase 1 tool surface the langcache MCP server exposes.
EXPECTED_TOOLS = {
    "create_long_term_memories",
    "search_long_term_memory",
    "get_long_term_memory",
    "edit_long_term_memory",
    "delete_long_term_memories",
    "get_session_memory",
    "set_session_memory",
}


def _headers() -> dict[str, str] | None:
  headers: dict[str, str] = {}
  if LANGCACHE_MCP_TOKEN:
    headers["X-API-Key"] = LANGCACHE_MCP_TOKEN
  if LANGCACHE_MCP_JWT:
    headers["Authorization"] = f"Bearer {LANGCACHE_MCP_JWT}"
  return headers or None


async def test_adk_mcptoolset_discovers_langcache_tools():
  """ADK's McpToolset should ingest the langcache tool schemas."""
  from google.adk.tools.mcp_tool import McpToolset
  from google.adk.tools.mcp_tool.mcp_session_manager import (
      StreamableHTTPConnectionParams,
  )

  toolset = McpToolset(
      connection_params=StreamableHTTPConnectionParams(
          url=LANGCACHE_MCP_URL, headers=_headers()
      ),
  )
  try:
    tools = await toolset.get_tools()
    names = {tool.name for tool in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"ADK did not discover langcache tools: {missing}"
  finally:
    await toolset.close()


async def test_create_get_search_round_trip():
  """Drive the langcache tools over MCP for a full memory round trip."""
  from mcp import ClientSession
  from mcp.client.streamable_http import streamablehttp_client

  memory_id = f"adk-{uuid.uuid4().hex}"
  owner = "adk-itest-owner"
  text = "The user prefers dark mode"

  async with streamablehttp_client(LANGCACHE_MCP_URL, headers=_headers()) as (
      read,
      write,
      _,
  ):
    async with ClientSession(read, write) as session:
      await session.initialize()

      created = await session.call_tool(
          "create_long_term_memories",
          {
              "memories": [
                  {
                      "id": memory_id,
                      "text": text,
                      "owner_id": owner,
                      "topics": ["preferences"],
                  }
              ]
          },
      )
      assert created.isError is False, created.content
      assert memory_id in created.structuredContent["created"]

      got = await session.call_tool(
          "get_long_term_memory", {"memory_id": memory_id}
      )
      assert got.isError is False, got.content
      assert got.structuredContent["memory"]["id"] == memory_id
      assert got.structuredContent["memory"]["text"] == text

      found = await session.call_tool(
          "search_long_term_memory", {"text": "dark mode", "owner_id": owner}
      )
      assert found.isError is False, found.content
      found_ids = [m["id"] for m in found.structuredContent["memories"]]
      assert memory_id in found_ids
