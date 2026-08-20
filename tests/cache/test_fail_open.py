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

"""A failing cache backend must not abort the ADK invocation.

ADK awaits before_model_callback and before_tool_callback with no
try/except, and outside its own model-error handling, so an exception
raised by a cache provider ends the turn with no events emitted. A cache
is an optimization, so both caches swallow provider failures and fall
through to the model or the tool.
"""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
import pytest

from adk_redis.cache._provider import BaseCacheProvider
from adk_redis.cache._provider import CacheEntry
from adk_redis.cache.llm_cache import LLMResponseCache
from adk_redis.cache.llm_cache import LLMResponseCacheConfig
from adk_redis.cache.tool_cache import ToolCache
from adk_redis.cache.tool_cache import ToolCacheConfig


class _BrokenProvider(BaseCacheProvider):
  """A provider whose backend is unreachable."""

  def __init__(self) -> None:
    self.check_calls = 0
    self.store_calls = 0

  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    self.check_calls += 1
    raise RuntimeError("backend unreachable")

  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> Optional[str]:
    self.store_calls += 1
    raise RuntimeError("backend unreachable")

  async def delete_by_id(self, entry_id: str, **kwargs: Any) -> None:
    raise RuntimeError("backend unreachable")

  async def clear(self, **kwargs: Any) -> None:
    raise RuntimeError("backend unreachable")

  async def close(self) -> None:
    return None


def _callback_context() -> MagicMock:
  """Build a callback context with no session history."""
  context = MagicMock()
  context.session = None
  return context


@pytest.mark.asyncio
class TestLLMResponseCacheFailsOpen:
  """LLMResponseCache degrades to a model call when the backend errors."""

  async def test_check_failure_falls_through_to_the_model(self):
    """A failed lookup returns None so ADK proceeds with the LLM call."""
    provider = _BrokenProvider()
    cache = LLMResponseCache(provider=provider)
    result = await cache.before_model_callback(
        _callback_context(), _user_request()
    )

    assert result is None
    assert provider.check_calls == 1

  async def test_store_failure_preserves_the_response(self):
    """A failed store returns None so the model response passes through."""
    provider = _BrokenProvider()
    cache = LLMResponseCache(provider=provider)
    context = _callback_context()
    request = _user_request()
    response = LlmResponse(
        content=types.Content(
            role="model", parts=[types.Part(text="An in-memory data store.")]
        )
    )

    # The lookup must register a pending prompt for the store to be tried,
    # so use a provider that only fails on write.
    provider.check = _miss  # type: ignore[method-assign]
    assert await cache.before_model_callback(context, request) is None

    result = await cache.after_model_callback(context, response)

    assert result is None
    assert provider.store_calls == 1


async def _miss(prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
  """Stand in for a lookup that completes and finds nothing."""
  return None


def _user_request(text: str = "What is Redis?") -> LlmRequest:
  """Build a request carrying a single user turn."""
  return LlmRequest(
      contents=[types.Content(role="user", parts=[types.Part(text=text)])]
  )


@pytest.mark.asyncio
class TestToolCacheFailsOpen:
  """ToolCache degrades to running the tool when the backend errors."""

  async def test_check_failure_falls_through_to_the_tool(self):
    """A failed lookup returns None so ADK executes the tool."""
    provider = _BrokenProvider()
    cache = ToolCache(provider=provider)
    tool = MagicMock()
    tool.name = "get_weather"

    result = await cache.before_tool_callback(
        tool=tool, args={"city": "London"}, tool_context=MagicMock()
    )

    assert result is None
    assert provider.check_calls == 1

  async def test_store_failure_preserves_the_tool_result(self):
    """A failed store returns None so the tool result passes through."""
    provider = _BrokenProvider()
    cache = ToolCache(provider=provider)
    provider.check = _miss  # type: ignore[method-assign]
    tool = MagicMock()
    tool.name = "get_weather"
    tool_context = MagicMock()

    await cache.before_tool_callback(
        tool=tool, args={"city": "London"}, tool_context=tool_context
    )
    result = await cache.after_tool_callback(
        tool=tool,
        args={"city": "London"},
        tool_context=tool_context,
        tool_response={"temp": 12},
    )

    assert result is None
    assert provider.store_calls == 1


@pytest.mark.asyncio
class TestIgnoreErrorsDisabled:
  """ignore_errors=False lets a developer see the failure directly."""

  async def test_llm_cache_raises_when_errors_are_not_ignored(self):
    """The provider's exception reaches the caller unchanged."""
    cache = LLMResponseCache(
        provider=_BrokenProvider(),
        config=LLMResponseCacheConfig(ignore_errors=False),
    )

    with pytest.raises(RuntimeError, match="backend unreachable"):
      await cache.before_model_callback(_callback_context(), _user_request())

  async def test_tool_cache_raises_when_errors_are_not_ignored(self):
    """The provider's exception reaches the caller unchanged."""
    cache = ToolCache(
        provider=_BrokenProvider(),
        config=ToolCacheConfig(ignore_errors=False),
    )
    tool = MagicMock()
    tool.name = "get_weather"

    with pytest.raises(RuntimeError, match="backend unreachable"):
      await cache.before_tool_callback(
          tool=tool, args={"city": "London"}, tool_context=MagicMock()
      )
