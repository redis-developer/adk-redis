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

"""Tests for create_redisvl_mcp_toolset."""

from __future__ import annotations

from pydantic import SecretStr
import pytest

pytest.importorskip("google.adk.tools.mcp_tool")

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StreamableHTTPConnectionParams,
)

from adk_redis.tools.mcp_search import create_redisvl_mcp_toolset
from adk_redis.tools.mcp_search import REDISVL_MCP_TOOL_SEARCH
from adk_redis.tools.mcp_search import REDISVL_MCP_TOOL_UPSERT


class TestCreateRedisVLMcpToolsetValidation:
  """Argument validation."""

  def test_requires_url_or_config_path(self):
    with pytest.raises(ValueError, match="url.*config_path"):
      create_redisvl_mcp_toolset()

  def test_url_and_config_path_are_mutually_exclusive(self):
    with pytest.raises(ValueError, match="mutually exclusive"):
      create_redisvl_mcp_toolset(
          url="http://localhost:8000",
          config_path="/etc/redisvl.yaml",
      )

  def test_stdio_requires_config_path(self):
    with pytest.raises(ValueError, match="config_path"):
      create_redisvl_mcp_toolset(transport="stdio", url="http://x")

  def test_url_transports_reject_config_path(self):
    with pytest.raises(ValueError):
      create_redisvl_mcp_toolset(
          transport="sse", config_path="/etc/redisvl.yaml"
      )

  def test_unknown_transport_raises_value_error(self):
    """Regression: typo in `transport` must fail loudly, not silently fall through."""
    with pytest.raises(ValueError, match="transport"):
      create_redisvl_mcp_toolset(
          url="http://localhost:8000/mcp",
          transport="stdioo",  # type: ignore[arg-type]
      )


class TestCreateRedisVLMcpToolsetStdio:
  """Stdio transport: spawn `rvl mcp --config <path>`."""

  def test_stdio_returns_mcp_toolset(self):
    toolset = create_redisvl_mcp_toolset(
        transport="stdio",
        config_path="/etc/redisvl.yaml",
    )
    assert isinstance(toolset, McpToolset)

  def test_stdio_connection_params_shape(self):
    toolset = create_redisvl_mcp_toolset(
        transport="stdio",
        config_path="/etc/redisvl.yaml",
    )
    params = toolset._connection_params
    assert isinstance(params, StdioConnectionParams)
    assert params.server_params.command == "rvl"
    assert "mcp" in params.server_params.args
    assert "--config" in params.server_params.args
    assert "/etc/redisvl.yaml" in params.server_params.args

  def test_stdio_read_only_flag_propagates(self):
    toolset = create_redisvl_mcp_toolset(
        transport="stdio",
        config_path="/etc/redisvl.yaml",
        read_only=True,
    )
    params = toolset._connection_params
    assert "--read-only" in params.server_params.args

  def test_stdio_no_read_only_when_false(self):
    toolset = create_redisvl_mcp_toolset(
        transport="stdio",
        config_path="/etc/redisvl.yaml",
        read_only=False,
    )
    params = toolset._connection_params
    assert "--read-only" not in params.server_params.args


class TestCreateRedisVLMcpToolsetStreamableHttp:
  """Streamable-HTTP transport: connect to a remote server."""

  def test_streamable_http_default(self):
    toolset = create_redisvl_mcp_toolset(url="http://localhost:8000/mcp")
    params = toolset._connection_params
    assert isinstance(params, StreamableHTTPConnectionParams)
    assert params.url == "http://localhost:8000/mcp"

  def test_streamable_http_bearer_token_in_headers(self):
    toolset = create_redisvl_mcp_toolset(
        url="http://localhost:8000/mcp",
        auth_token=SecretStr("s3cret"),
    )
    params = toolset._connection_params
    assert params.headers is not None
    assert params.headers.get("Authorization") == "Bearer s3cret"

  def test_streamable_http_no_headers_without_token(self):
    toolset = create_redisvl_mcp_toolset(url="http://localhost:8000/mcp")
    params = toolset._connection_params
    assert params.headers is None or "Authorization" not in (
        params.headers or {}
    )


class TestCreateRedisVLMcpToolsetSse:
  """SSE transport: connect to a remote SSE server."""

  def test_sse_returns_correct_params(self):
    toolset = create_redisvl_mcp_toolset(
        url="http://localhost:8000/sse",
        transport="sse",
    )
    params = toolset._connection_params
    assert isinstance(params, SseConnectionParams)
    assert params.url == "http://localhost:8000/sse"

  def test_sse_bearer_token_in_headers(self):
    toolset = create_redisvl_mcp_toolset(
        url="http://localhost:8000/sse",
        transport="sse",
        auth_token=SecretStr("t"),
    )
    params = toolset._connection_params
    assert params.headers.get("Authorization") == "Bearer t"


class TestCreateRedisVLMcpToolsetFilterAndConstants:
  """Tool filter and exported tool-name constants."""

  def test_tool_filter_passthrough(self):
    toolset = create_redisvl_mcp_toolset(
        url="http://localhost:8000/mcp",
        tool_filter=[REDISVL_MCP_TOOL_SEARCH],
    )
    assert toolset.tool_filter == [REDISVL_MCP_TOOL_SEARCH]

  def test_exports_known_tool_constants(self):
    assert REDISVL_MCP_TOOL_SEARCH == "search-records"
    assert REDISVL_MCP_TOOL_UPSERT == "upsert-records"
