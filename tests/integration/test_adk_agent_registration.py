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

"""End-to-end ADK Agent registration tests.

These tests confirm search tools register cleanly with
``google.adk.Agent`` and surface a usable ``FunctionDeclaration``. They
also confirm a native ADK ``McpToolset`` pointed at the RedisVL MCP
server attaches to an Agent. No LLM calls; runs without API keys.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("google.adk")
pytest.importorskip("redisvl")

from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters
from redisvl.index import SearchIndex

from adk_redis import RedisSQLSearchTool
from adk_redis import RedisTextQueryConfig
from adk_redis import RedisTextSearchTool


class TestSearchToolsRegisterWithAgent:
  """Agent.canonical_tools surfaces every search tool it was handed."""

  @pytest.mark.asyncio
  async def test_sql_search_tool_registers(self):
    index = MagicMock(spec=SearchIndex)
    tool = RedisSQLSearchTool(index=index)
    agent = Agent(
        model="gemini-2.5-flash",
        name="test_agent",
        tools=[tool],
    )

    ctx = MagicMock(spec=ReadonlyContext)
    tools = await agent.canonical_tools(ctx)

    names = [t.name for t in tools]
    assert "redis_sql_search" in names

  @pytest.mark.asyncio
  async def test_text_search_tool_registers(self):
    index = MagicMock(spec=SearchIndex)
    tool = RedisTextSearchTool(
        index=index, config=RedisTextQueryConfig(stopwords=None)
    )
    agent = Agent(
        model="gemini-2.5-flash",
        name="test_agent",
        tools=[tool],
    )

    ctx = MagicMock(spec=ReadonlyContext)
    tools = await agent.canonical_tools(ctx)

    names = [t.name for t in tools]
    assert "redis_text_search" in names


class TestRedisVLMcpToolsetRegistersWithAgent:
  """A native ADK McpToolset against rvl mcp attaches to an Agent."""

  def test_streamable_http_toolset_registers(self):
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="http://localhost:8000/mcp",
        ),
        tool_filter=["search-records"],
    )
    agent = Agent(
        model="gemini-2.5-flash",
        name="test_agent",
        tools=[toolset],
    )
    assert toolset in agent.tools

  def test_stdio_toolset_registers(self):
    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="rvl",
                args=[
                    "mcp",
                    "--config",
                    "/etc/redisvl/mcp.yaml",
                    "--read-only",
                ],
            ),
            timeout=30,
        ),
        tool_filter=["search-records"],
    )
    agent = Agent(
        model="gemini-2.5-flash",
        name="test_agent",
        tools=[toolset],
    )
    assert toolset in agent.tools
