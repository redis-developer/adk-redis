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

Connects an ADK agent to a running `rvl mcp` server via
`create_redisvl_mcp_toolset(...)` over the streamable-http transport.
The MCP server (configured by `../mcp_config.yaml`) exposes one
`search-records` tool over BM25 fulltext on the `content` field of the
`adk_mcp_articles` index.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from pydantic import SecretStr

from adk_redis import create_redisvl_mcp_toolset

INSTRUCTION = """You are a Redis docs assistant. You have a single MCP tool,
`search-records`, that runs BM25 fulltext search over a Redis index of
articles about Redis search, caching, memory, and the MCP server itself.

For any question:

1. Decide which keywords from the user's question are most likely to appear
   in a relevant article (e.g., "HNSW", "FT.HYBRID", "semantic cache").
2. Call `search-records` with that query. You can pass `limit` (default 5).
3. Summarize the top matches and cite each article's title and URL.

If the tool returns no matches, say so plainly. Do not fabricate articles.
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
