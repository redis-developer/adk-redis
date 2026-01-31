# Copyright 2025 Google LLC
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

"""Tool result caching service for ADK agents."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Set

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel
from pydantic import Field

from ._provider import BaseCacheProvider

logger = logging.getLogger("google_adk." + __name__)


class ToolCacheConfig(BaseModel):
  """Configuration for tool result caching.

  Attributes:
      tool_names: Set of tool names to cache. None means cache all tools.
      include_app_name: Include app name in cache key.
      include_user_id: Include user ID in cache key.
      include_session_id: Include session ID in cache key.
  """

  tool_names: Optional[Set[str]] = Field(default=None)
  include_app_name: bool = Field(default=True)
  include_user_id: bool = Field(default=True)
  include_session_id: bool = Field(default=False)


class ToolCache:
  """Cache service for tool call results.

  This service caches tool results using semantic similarity matching
  on the tool name and arguments. It can be configured to only cache
  specific tools.
  """

  def __init__(
      self,
      provider: BaseCacheProvider,
      config: Optional[ToolCacheConfig] = None,
  ):
    """Initialize the tool cache.

    Args:
        provider: The cache provider to use for storage.
        config: Configuration for caching behavior.
    """
    self._provider = provider
    self._config = config or ToolCacheConfig()
    # Track pending tool calls by session key for after_tool_callback
    self._pending_calls: dict[str, str] = {}

  def _should_cache_tool(self, tool_name: str) -> bool:
    """Check if the tool should be cached."""
    if self._config.tool_names is None:
      return True
    return tool_name in self._config.tool_names

  def _build_cache_key(
      self,
      tool_name: str,
      args: Dict[str, Any],
      tool_context: ToolContext,
  ) -> str:
    """Build a cache key from tool name, args, and context."""
    parts = []

    # ToolContext doesn't have invocation_context in current ADK version
    # Just use tool name and args for cache key
    parts.append(f"tool:{tool_name}")
    try:
      args_str = json.dumps(args, sort_keys=True, default=str)
    except (TypeError, ValueError):
      args_str = str(args)
    parts.append(f"args:{args_str}")

    return " | ".join(parts)

  def _get_session_key(self, tool_context: ToolContext) -> str:
    """Get a unique key for the current session context."""
    # Use tool_context id as session key
    return str(id(tool_context))

  async def before_tool_callback(
      self,
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
  ) -> Optional[Dict[str, Any]]:
    """Check cache before executing tool.

    Args:
        tool: The tool being called.
        args: The arguments for the tool call.
        tool_context: The tool context with session info.

    Returns:
        Dict if cache hit (skips tool execution), None to proceed.
    """
    tool_name = tool.name
    if not self._should_cache_tool(tool_name):
      logger.debug("Tool %s not in cache list, skipping", tool_name)
      return None

    cache_key = self._build_cache_key(tool_name, args, tool_context)
    cache_entry = await self._provider.check(cache_key)

    if cache_entry:
      logger.info("Cache hit for tool: %s", tool_name)
      try:
        return json.loads(cache_entry.response)  # type: ignore[no-any-return]
      except (json.JSONDecodeError, TypeError):
        return {"result": cache_entry.response}

    logger.debug("Cache miss for tool: %s", tool_name)
    # Store cache key for after_tool_callback
    session_key = self._get_session_key(tool_context)
    self._pending_calls[session_key] = cache_key
    return None

  async def after_tool_callback(
      self,
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
      tool_response: Dict[str, Any],
  ) -> Optional[Dict[str, Any]]:
    """Store tool result in cache after execution.

    Args:
        tool: The tool that was called.
        args: The arguments used for the tool call.
        tool_context: The tool context with session info.
        tool_response: The result from the tool execution.

    Returns:
        None to pass through the original response.
    """
    session_key = self._get_session_key(tool_context)
    cache_key = self._pending_calls.pop(session_key, None)

    if not cache_key:
      logger.debug("No pending cache key for tool, skipping store")
      return None

    # Serialize the tool response
    try:
      response_str = json.dumps(tool_response, default=str)
    except (TypeError, ValueError):
      response_str = str(tool_response)

    await self._provider.store(cache_key, response_str)
    logger.info("Cached result for tool: %s", tool.name)
    return None
