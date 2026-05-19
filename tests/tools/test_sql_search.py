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

"""Tests for RedisSQLSearchTool."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

pytest.importorskip("redisvl")

from redisvl.index import SearchIndex
from redisvl.query import SQLQuery

from adk_redis.tools import RedisSQLSearchTool


@pytest.fixture
def mock_index():
  """Mock RedisVL SearchIndex."""
  index = MagicMock(spec=SearchIndex)
  index.query = MagicMock(
      return_value=[
          {"title": "Doc A", "price": 42, "category": "electronics"},
          {"title": "Doc B", "price": 11, "category": "electronics"},
      ]
  )
  return index


@pytest.fixture
def sql_search_tool(mock_index):
  """A SQL search tool bound to a mock index."""
  return RedisSQLSearchTool(index=mock_index)


class TestRedisSQLSearchToolInit:
  """Construction surface."""

  def test_default_name_and_description(self, mock_index):
    tool = RedisSQLSearchTool(index=mock_index)
    assert tool.name == "redis_sql_search"
    assert "SQL" in tool.description or "SELECT" in tool.description

  def test_custom_name_and_description(self, mock_index):
    tool = RedisSQLSearchTool(
        index=mock_index,
        name="catalog_query",
        description="Query the catalog via SQL.",
    )
    assert tool.name == "catalog_query"
    assert tool.description == "Query the catalog via SQL."

  def test_sql_redis_options_stored(self, mock_index):
    tool = RedisSQLSearchTool(
        index=mock_index,
        sql_redis_options={"schema_cache_strategy": "load_all"},
    )
    assert tool._sql_redis_options == {"schema_cache_strategy": "load_all"}

  def test_no_vectorizer_required(self, mock_index):
    tool = RedisSQLSearchTool(index=mock_index)
    assert not hasattr(tool, "_vectorizer")


class TestRedisSQLSearchToolDeclaration:
  """Function declaration shape exposed to the LLM."""

  def test_declares_sql_parameter(self, sql_search_tool):
    declaration = sql_search_tool._get_declaration()
    assert declaration.name == "redis_sql_search"
    assert "sql" in declaration.parameters.properties
    assert "sql" in declaration.parameters.required

  def test_declares_optional_params(self, sql_search_tool):
    declaration = sql_search_tool._get_declaration()
    assert "params" in declaration.parameters.properties
    assert "params" not in declaration.parameters.required


class TestRedisSQLSearchToolRunAsync:
  """Async execution path."""

  @pytest.mark.asyncio
  @patch("adk_redis.tools.search._base.asyncio.to_thread")
  async def test_run_async_success(
      self, mock_to_thread, sql_search_tool, mock_index
  ):
    """SELECT statement is routed to SQLQuery and the index."""
    mock_to_thread.return_value = [
        {"title": "Doc A", "price": 42, "category": "electronics"}
    ]
    mock_context = MagicMock()

    with patch(
        "adk_redis.tools.search.sql.SQLQuery", wraps=SQLQuery
    ) as wrapped_query:
      result = await sql_search_tool.run_async(
          args={
              "sql": "SELECT title, price, category FROM catalog WHERE price < 100"
          },
          tool_context=mock_context,
      )

    assert result["status"] == "success"
    assert result["count"] == 1
    assert len(result["results"]) == 1
    wrapped_query.assert_called_once()
    _, kwargs = wrapped_query.call_args
    assert (
        kwargs["sql"]
        == "SELECT title, price, category FROM catalog WHERE price < 100"
    )

  @pytest.mark.asyncio
  @patch("adk_redis.tools.search._base.asyncio.to_thread")
  async def test_run_async_passes_params(
      self, mock_to_thread, sql_search_tool, mock_index
  ):
    """Caller-supplied params dict reaches SQLQuery."""
    mock_to_thread.return_value = []
    mock_context = MagicMock()

    with patch(
        "adk_redis.tools.search.sql.SQLQuery", wraps=SQLQuery
    ) as wrapped_query:
      await sql_search_tool.run_async(
          args={
              "sql": "SELECT * FROM catalog WHERE price < :max_price",
              "params": {"max_price": 50},
          },
          tool_context=mock_context,
      )

    _, kwargs = wrapped_query.call_args
    assert kwargs["params"] == {"max_price": 50}

  @pytest.mark.asyncio
  @patch("adk_redis.tools.search._base.asyncio.to_thread")
  async def test_run_async_passes_sql_redis_options(
      self, mock_to_thread, mock_index
  ):
    """sql_redis_options from config reaches SQLQuery."""
    tool = RedisSQLSearchTool(
        index=mock_index,
        sql_redis_options={"schema_cache_strategy": "load_all"},
    )
    mock_to_thread.return_value = []
    mock_context = MagicMock()

    with patch(
        "adk_redis.tools.search.sql.SQLQuery", wraps=SQLQuery
    ) as wrapped_query:
      await tool.run_async(
          args={"sql": "SELECT * FROM catalog"},
          tool_context=mock_context,
      )

    _, kwargs = wrapped_query.call_args
    assert kwargs["sql_redis_options"] == {"schema_cache_strategy": "load_all"}

  @pytest.mark.asyncio
  async def test_run_async_empty_sql(self, sql_search_tool):
    """Empty SQL returns an error result, not an exception."""
    mock_context = MagicMock()
    result = await sql_search_tool.run_async(
        args={"sql": ""},
        tool_context=mock_context,
    )
    assert result["status"] == "error"
    assert "required" in result["error"].lower()

  @pytest.mark.asyncio
  @patch("adk_redis.tools.search._base.asyncio.to_thread")
  async def test_run_async_query_error_returns_error_status(
      self, mock_to_thread, sql_search_tool
  ):
    """Underlying query error is surfaced as status=error, not raised."""
    mock_to_thread.side_effect = RuntimeError("schema not found")
    mock_context = MagicMock()
    result = await sql_search_tool.run_async(
        args={"sql": "SELECT * FROM missing_index"},
        tool_context=mock_context,
    )
    assert result["status"] == "error"
    assert "schema not found" in result["error"]
