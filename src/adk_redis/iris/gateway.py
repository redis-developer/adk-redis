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

"""Expose a Context Gateway catalog as Google ADK tools."""

from copy import deepcopy
from typing import Any

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.base_toolset import ToolPredicate
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from redis_iris.context_gateway import ContextGateway
from redis_iris.context_gateway import GatewayTool
from redis_iris.context_gateway.gateway import model_names
from redis_iris.errors import ToolError


class _GatewayTool(BaseTool):
  """Translate one Gateway MCP declaration and its response to ADK."""

  def __init__(
      self, gateway: ContextGateway, definition: GatewayTool, alias: str
  ) -> None:
    super().__init__(name=alias, description=definition.description)
    self._gateway = gateway
    self._definition = definition

  def _get_declaration(self) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters_json_schema=deepcopy(self._definition.input_schema),
    )

  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> dict[str, Any]:
    """Invoke the original Gateway name with the ADK tool arguments."""
    try:
      result = await self._gateway.acall(self._definition.name, args)
    except ToolError as error:
      return {"error": str(error)}
    if result.is_error:
      return {"error": result.as_text()}
    return {
        "result": result.data if result.data is not None else result.as_text()
    }


class IrisGatewayToolset(BaseToolset):
  """Discover and call Context Gateway tools through the Iris SDK.

  Full mode exposes the catalog. Search mode exposes the Gateway's search,
  dispatch and result tools. Each tool preserves the published JSON Schema.

  Args:
      gateway: A configured SDK client. Defaults to the Iris environment.
      tool_filter: ADK tool names or a predicate used to filter declarations.
      refresh: Refresh the Gateway catalog at each ADK tool discovery.
  """

  def __init__(
      self,
      gateway: ContextGateway | None = None,
      *,
      tool_filter: list[str] | ToolPredicate | None = None,
      refresh: bool = False,
  ) -> None:
    super().__init__(tool_filter=tool_filter)
    self._gateway = (
        gateway if gateway is not None else ContextGateway.from_env()
    )
    self._refresh = refresh

  async def get_tools(
      self, readonly_context: ReadonlyContext | None = None
  ) -> list[BaseTool]:
    """Return the SDK catalog as ADK tools."""
    definitions = await self._gateway.atools(refresh=self._refresh)
    by_name = {tool.name: tool for tool in definitions}
    names = model_names([tool.name for tool in definitions])
    tools: list[BaseTool] = [
        _GatewayTool(self._gateway, by_name[name], alias)
        for alias, name in names.items()
    ]
    return [
        tool for tool in tools if self._is_tool_selected(tool, readonly_context)
    ]
