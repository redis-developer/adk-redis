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

The MCP-path mirror of `examples/redis_search_tools/`. It targets the
same knowledge-base corpus but routes search through a separately-running
`rvl mcp` server via `create_redisvl_mcp_toolset(...)`. The server is
configured for hybrid (BM25 + vector) search, so a single MCP tool
covers both semantic and keyword retrieval.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from pydantic import SecretStr

from adk_redis import create_redisvl_mcp_toolset

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


def create_agent() -> Agent:
  """Create the RedisVL MCP search agent."""
  load_dotenv(Path(__file__).parent.parent / ".env")

  mcp_url = os.getenv("REDISVL_MCP_URL", "http://127.0.0.1:8765/mcp")
  auth_token = os.getenv("REDISVL_MCP_AUTH_TOKEN")

  toolset = create_redisvl_mcp_toolset(
      url=mcp_url,
      transport="streamable-http",
      auth_token=SecretStr(auth_token) if auth_token else None,
      tool_filter=["search-records"],
  )

  return Agent(
      model="gemini-2.5-flash",
      name="redisvl_mcp_search_agent",
      instruction=INSTRUCTION,
      tools=[toolset],
  )


root_agent = create_agent()


if __name__ == "__main__":
  print(
      f"Agent '{root_agent.name}' loaded with {len(root_agent.tools)} toolset(s)"
  )
