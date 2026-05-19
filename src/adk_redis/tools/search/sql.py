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

"""Redis SQL search tool wrapping redisvl.query.SQLQuery."""

from __future__ import annotations

from typing import Any

from google.adk.tools.tool_context import ToolContext
from google.genai import types
from redisvl.index import AsyncSearchIndex
from redisvl.index import SearchIndex
from redisvl.query import SQLQuery

from adk_redis.tools.search._base import BaseRedisSearchTool

_DEFAULT_DESCRIPTION = (
    "Run a SQL SELECT statement against the bound Redis search index. "
    "Use SQL-style filters (=, LIKE, fulltext, fuzzy, BETWEEN). Parameter "
    "substitution is supported via :name placeholders in the SQL and a "
    "matching params object."
)


class RedisSQLSearchTool(BaseRedisSearchTool):
  """Search tool that lets the LLM issue SQL SELECT statements.

  Wraps ``redisvl.query.SQLQuery``, which translates SQL into Redis
  ``FT.SEARCH`` / ``FT.AGGREGATE`` commands via the optional ``sql-redis``
  extra. Use this when an agent benefits from expressing filters and
  projections directly in SQL rather than configuring query parameters
  field by field.

  Example:
      ```python
      from redisvl.index import SearchIndex
      from adk_redis import RedisSQLSearchTool

      index = SearchIndex.from_yaml("schema.yaml")
      tool = RedisSQLSearchTool(index=index)

      agent = Agent(model="gemini-2.5-flash", tools=[tool])
      ```

  Note:
      Requires the ``sql-redis`` optional dependency. Install with
      ``pip install 'adk-redis[sql]'``.
  """

  def __init__(
      self,
      *,
      index: SearchIndex | AsyncSearchIndex,
      sql_redis_options: dict[str, Any] | None = None,
      return_fields: list[str] | None = None,
      name: str = "redis_sql_search",
      description: str = _DEFAULT_DESCRIPTION,
  ):
    """Initialize the SQL search tool.

    Args:
        index: The RedisVL SearchIndex or AsyncSearchIndex to query.
        sql_redis_options: Optional passthrough options forwarded to the
            sql-redis executor. For example, ``{"schema_cache_strategy":
            "load_all"}`` eagerly loads index schemas. The redisvl default
            is lazy loading.
        return_fields: Ignored. SQL SELECT clauses already specify the
            projection. Accepted for API symmetry with sibling tools.
        name: The name of the tool (exposed to LLM).
        description: The description of the tool (exposed to LLM).
    """
    super().__init__(
        name=name,
        description=description,
        index=index,
        return_fields=return_fields,
    )
    self._sql_redis_options = sql_redis_options or {}

  def _get_declaration(self) -> types.FunctionDeclaration:
    """Get the function declaration for the LLM."""
    return types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "sql": types.Schema(
                    type=types.Type.STRING,
                    description=(
                        "A SQL SELECT statement to execute. Use :param "
                        "placeholders for values and supply them via the "
                        "params object."
                    ),
                ),
                "params": types.Schema(
                    type=types.Type.OBJECT,
                    description=(
                        "Optional parameter map for :name placeholders "
                        "in the SQL."
                    ),
                ),
            },
            required=["sql"],
        ),
    )

  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> dict[str, Any]:
    """Execute the SQL query.

    Args:
        args: Arguments from the LLM. Must include ``sql``. May include
            ``params``.
        tool_context: The tool execution context.

    Returns:
        Dictionary with status, count, and results (or error).
    """
    sql_text = args.get("sql", "")
    if not sql_text:
      return {"status": "error", "error": "SQL statement is required."}

    try:
      query = SQLQuery(
          sql=sql_text,
          params=args.get("params"),
          sql_redis_options=self._sql_redis_options or None,
      )
      results = await self._execute_query(query)
      return {
          "status": "success",
          "count": len(results),
          "results": results,
      }
    except Exception as e:  # noqa: BLE001
      return {"status": "error", "error": str(e)}
