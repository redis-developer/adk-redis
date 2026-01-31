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

"""Factory functions for creating cache-enabled callbacks."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from .llm_response_cache import LLMResponseCache
from .tool_cache import ToolCache

# Type aliases for callback signatures
BeforeModelCallback = Callable[
    [CallbackContext, LlmRequest],
    Optional[LlmResponse],
]
AfterModelCallback = Callable[
    [CallbackContext, LlmResponse],
    Optional[LlmResponse],
]
BeforeToolCallback = Callable[
    [BaseTool, Dict[str, Any], ToolContext],
    Optional[Dict[str, Any]],
]
AfterToolCallback = Callable[
    [BaseTool, Dict[str, Any], ToolContext, Dict[str, Any]],
    Optional[Dict[str, Any]],
]


def create_llm_cache_callbacks(
    cache: LLMResponseCache,
) -> Tuple[BeforeModelCallback, AfterModelCallback]:
  """Create callback functions for LLM response caching.

  This factory function wraps the LLMResponseCache methods into standalone
  callback functions compatible with ADK's Agent constructor.

  Args:
      cache: The LLMResponseCache instance to use.

  Returns:
      A tuple of (before_model_callback, after_model_callback) functions.

  Example:
      ```python
      llm_cache = LLMResponseCache(provider=provider)
      before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

      agent = Agent(
          name="my_agent",
          before_model_callback=before_cb,
          after_model_callback=after_cb,
      )
      ```
  """

  async def before_model_callback(
      callback_context: CallbackContext,
      llm_request: LlmRequest,
  ) -> Optional[LlmResponse]:
    return await cache.before_model_callback(callback_context, llm_request)  # type: ignore[return-value,no-any-return]

  async def after_model_callback(
      callback_context: CallbackContext,
      llm_response: LlmResponse,
  ) -> Optional[LlmResponse]:
    return await cache.after_model_callback(callback_context, llm_response)  # type: ignore[return-value,no-any-return]

  return before_model_callback, after_model_callback  # type: ignore[return-value]


def create_tool_cache_callbacks(
    cache: ToolCache,
) -> Tuple[BeforeToolCallback, AfterToolCallback]:
  """Create callback functions for tool result caching.

  This factory function wraps the ToolCache methods into standalone
  callback functions compatible with ADK's Agent constructor.

  Args:
      cache: The ToolCache instance to use.

  Returns:
      A tuple of (before_tool_callback, after_tool_callback) functions.

  Example:
      ```python
      tool_cache = ToolCache(provider=provider)
      before_cb, after_cb = create_tool_cache_callbacks(tool_cache)

      agent = Agent(
          name="my_agent",
          before_tool_callback=before_cb,
          after_tool_callback=after_cb,
      )
      ```
  """

  async def before_tool_callback(
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
  ) -> Optional[Dict[str, Any]]:
    return await cache.before_tool_callback(tool, args, tool_context)  # type: ignore[return-value]

  async def after_tool_callback(
      tool: BaseTool,
      args: Dict[str, Any],
      tool_context: ToolContext,
      tool_response: Dict[str, Any],
  ) -> Optional[Dict[str, Any]]:
    return await cache.after_tool_callback(  # type: ignore[return-value]
        tool, args, tool_context, tool_response
    )

  return before_tool_callback, after_tool_callback  # type: ignore[return-value]
