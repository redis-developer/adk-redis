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

"""Helper for binding ADK to a RedisVL MCP server (`rvl mcp`).

This module exposes ``create_redisvl_mcp_toolset(...)``, which returns an
``McpToolset`` wired to a RedisVL MCP server. The server is shipped by the
``redisvl[mcp]`` extra and exposes index-aware ``search-records`` and
``upsert-records`` tools whose descriptions include filter and return-field
hints derived from the bound index schema.

Three transport modes are supported:

- ``stdio``: spawn ``rvl mcp --config <path>`` in-process. Pass ``config_path``.
- ``streamable-http``: connect to a remote server. Pass ``url``. (default)
- ``sse``: connect to a remote SSE server. Pass ``url``.

Read-only mode is on by default and is the safer choice for agents that
should not write.
"""

from __future__ import annotations

from typing import Any, Literal, TYPE_CHECKING

from pydantic import SecretStr

if TYPE_CHECKING:
  from google.adk.tools.mcp_tool import McpToolset


REDISVL_MCP_TOOL_SEARCH = "search-records"
REDISVL_MCP_TOOL_UPSERT = "upsert-records"

ALL_REDISVL_MCP_TOOLS = [
    REDISVL_MCP_TOOL_SEARCH,
    REDISVL_MCP_TOOL_UPSERT,
]


def create_redisvl_mcp_toolset(
    *,
    url: str | None = None,
    config_path: str | None = None,
    transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http",
    read_only: bool = True,
    auth_token: SecretStr | None = None,
    tool_filter: list[str] | None = None,
    timeout: float = 5.0,
) -> "McpToolset":
  """Create an MCP toolset pointed at a RedisVL MCP server.

  Args:
      url: URL of a running RedisVL MCP server. Required for ``sse`` and
          ``streamable-http`` transports. Mutually exclusive with
          ``config_path``.
      config_path: Path to a RedisVL MCP YAML config. When set, the helper
          spawns ``rvl mcp --config <path>`` over stdio. Required for the
          ``stdio`` transport. Mutually exclusive with ``url``.
      transport: Transport to use. Defaults to ``streamable-http``.
      read_only: Whether to pass ``--read-only`` to the spawned server.
          Only relevant in stdio mode. Default ``True``.
      auth_token: Optional bearer token for HTTP transports. Sent as
          ``Authorization: Bearer <token>``.
      tool_filter: Optional list of MCP tool names to expose. Use
          ``REDISVL_MCP_TOOL_SEARCH`` / ``REDISVL_MCP_TOOL_UPSERT`` for
          symbolic filtering.
      timeout: Connection timeout in seconds.

  Returns:
      A configured ``McpToolset``.

  Raises:
      ValueError: If ``url`` and ``config_path`` are both set or both unset,
          or if a transport / param combination is invalid.
      ImportError: If ``google-adk`` was installed without MCP support.

  Example:
      ```python
      from google.adk import Agent
      from adk_redis.tools.mcp_search import create_redisvl_mcp_toolset

      # Remote server, read-only.
      toolset = create_redisvl_mcp_toolset(
          url="http://localhost:8000/mcp",
      )

      # Local in-process stdio.
      toolset = create_redisvl_mcp_toolset(
          transport="stdio",
          config_path="/etc/redisvl/mcp.yaml",
      )

      agent = Agent(model="gemini-2.5-flash", tools=[toolset])
      ```
  """
  _VALID_TRANSPORTS = ("stdio", "sse", "streamable-http")
  if transport not in _VALID_TRANSPORTS:
    raise ValueError(
        f"Unknown transport {transport!r}. "
        f"Expected one of: {', '.join(_VALID_TRANSPORTS)}."
    )
  if url is None and config_path is None:
    raise ValueError(
        "create_redisvl_mcp_toolset requires either url or config_path."
    )
  if url is not None and config_path is not None:
    raise ValueError(
        "url and config_path are mutually exclusive: stdio uses config_path,"
        " HTTP/SSE transports use url."
    )
  if transport == "stdio" and config_path is None:
    raise ValueError("stdio transport requires config_path.")
  if transport in ("sse", "streamable-http") and url is None:
    raise ValueError(f"{transport} transport requires url.")

  try:
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        SseConnectionParams,
    )
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StdioConnectionParams,
    )
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        StreamableHTTPConnectionParams,
    )
    from mcp import StdioServerParameters
  except ImportError as e:
    raise ImportError(
        "google-adk with MCP support is required. Install it with: "
        "pip install 'google-adk[mcp]'"
    ) from e

  connection_params: Any
  if transport == "stdio":
    args = ["mcp", "--config", str(config_path)]
    if read_only:
      args.append("--read-only")
    connection_params = StdioConnectionParams(
        server_params=StdioServerParameters(command="rvl", args=args),
        timeout=timeout,
    )
  else:
    headers: dict[str, str] | None = None
    if auth_token is not None:
      headers = {"Authorization": f"Bearer {auth_token.get_secret_value()}"}
    if transport == "sse":
      connection_params = SseConnectionParams(
          url=str(url), headers=headers, timeout=timeout
      )
    else:
      connection_params = StreamableHTTPConnectionParams(
          url=str(url), headers=headers, timeout=timeout
      )

  return McpToolset(
      connection_params=connection_params,
      tool_filter=tool_filter,
  )
