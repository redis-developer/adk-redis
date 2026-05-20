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

"""RedisVL MCP search agent.

The MCP-path counterpart of `examples/redis_search_tools/`. It targets
a similar Redis knowledge-base corpus (overlapping, with MCP-specific
docs added in the loader) and routes search through a
separately-running `rvl mcp` server via ADK's native ``McpToolset``.
The server is configured for hybrid (BM25 + vector) search, so a
single MCP tool covers both semantic and keyword retrieval.

The agent does not depend on any adk-redis MCP wrapper; it uses the
standard ADK MCP pattern shown by every catalog integration page so the
same shape works against any MCP server.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

INSTRUCTION = """You are a helpful assistant with a technical knowledge base
served via an MCP server. You have one tool: `search-records`, configured
for hybrid search (BM25 text + vector similarity) over the
`adk_mcp_knowledge_base` index.

## When to call search-records

- Conceptual questions ("how does RAG work?") -> hybrid will lean on vector
  similarity.
- Technical terms / acronyms ("HNSW", "FT.HYBRID", "BM25") -> hybrid keeps
  exact keyword matches via the BM25 component.
- Comparative or "everything about X" questions -> hybrid combines both
  paths and ranks by the configured fusion method (LINEAR by default).

Pass a natural-language query in the `query` argument. The MCP server
embeds it server-side using `redis/langcache-embed-v2`. Optionally pass
`limit` (default 5).

## Response style

After calling `search-records`, summarize the matches for the user. Cite
each document's title and url. If the tool returns no matches, say so
plainly; do not fabricate results.

Available document categories: redis, adk, concepts, tutorials.
Document types: reference, tutorial, faq, api.
Difficulty levels: beginner, intermediate, advanced.
"""

DEFAULT_MCP_CONFIG_PATH = str(Path(__file__).parent.parent / "mcp_config.yaml")


def _build_toolset() -> McpToolset:
  """Pick stdio or streamable-http based on env vars.

  - If `REDISVL_MCP_URL` is set, connect to the running server over
    streamable-http. Optional `REDISVL_MCP_AUTH_TOKEN` becomes a bearer
    header.
  - Otherwise, spawn `rvl mcp --config <path> --read-only` over stdio.
    `REDISVL_MCP_CONFIG` overrides the default config path.
  """
  remote_url = os.getenv("REDISVL_MCP_URL")
  if remote_url:
    auth_token = os.getenv("REDISVL_MCP_AUTH_TOKEN")
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=remote_url,
            headers=headers,
            timeout=30,
        ),
        tool_filter=["search-records"],
    )

  config_path = os.getenv("REDISVL_MCP_CONFIG", DEFAULT_MCP_CONFIG_PATH)
  return McpToolset(
      connection_params=StdioConnectionParams(
          server_params=StdioServerParameters(
              command="rvl",
              args=["mcp", "--config", config_path, "--read-only"],
          ),
          timeout=30,
      ),
      tool_filter=["search-records"],
  )


def create_agent() -> Agent:
  """Create the RedisVL MCP search agent."""
  load_dotenv(Path(__file__).parent.parent / ".env")
  return Agent(
      model="gemini-2.5-flash",
      name="redisvl_mcp_search_agent",
      instruction=INSTRUCTION,
      tools=[_build_toolset()],
  )


root_agent = create_agent()


if __name__ == "__main__":
  print(
      f"Agent '{root_agent.name}' loaded with"
      f" {len(root_agent.tools)} toolset(s)"
  )
