# Copyright 2025 Google LLC
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

"""LLM response caching service for ADK agents."""

from __future__ import annotations

import logging
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import BaseModel
from pydantic import Field

from ._provider import BaseCacheProvider

logger = logging.getLogger("google_adk." + __name__)


class LLMResponseCacheConfig(BaseModel):
  """Configuration for LLM response caching.

  Attributes:
      first_message_only: Only cache first message in session.
      include_app_name: Include app name in cache key.
      include_user_id: Include user ID in cache key.
      include_session_id: Include session ID in cache key.
  """

  first_message_only: bool = Field(default=True)
  include_app_name: bool = Field(default=True)
  include_user_id: bool = Field(default=True)
  include_session_id: bool = Field(default=False)


class LLMResponseCache:
  """Cache service for LLM responses.

  This service caches LLM responses using semantic similarity matching.
  It can be configured to only cache first messages in a session to
  reduce API costs for common initial queries.
  """

  def __init__(
      self,
      provider: BaseCacheProvider,
      config: Optional[LLMResponseCacheConfig] = None,
  ):
    """Initialize the LLM response cache.

    Args:
        provider: The cache provider to use for storage.
        config: Configuration for caching behavior.
    """
    self._provider = provider
    self._config = config or LLMResponseCacheConfig()
    # Track pending prompts by session ID for after_model_callback
    self._pending_prompts: dict[str, str] = {}

  def _is_first_message(self, callback_context: CallbackContext) -> bool:
    """Check if this is the first user message in the session."""
    session = callback_context.session
    if not session or not session.events:
      return True

    user_message_count = sum(
        1 for event in session.events if event.author == "user"
    )
    return user_message_count == 0

  def _build_cache_key(
      self, prompt: str, callback_context: CallbackContext
  ) -> str:
    """Build a cache key from the prompt and context."""
    parts = []
    session = callback_context.session

    if self._config.include_app_name and session:
      parts.append(f"app:{session.app_name}")
    if self._config.include_user_id and session:
      parts.append(f"user:{session.user_id}")
    if self._config.include_session_id and session:
      parts.append(f"session:{session.id}")

    parts.append(prompt)
    return " | ".join(parts)

  def _extract_prompt(self, llm_request: LlmRequest) -> Optional[str]:
    """Extract the user prompt from the LLM request."""
    if not llm_request.contents:
      return None

    # Get the last user message
    for content in reversed(llm_request.contents):
      if content.role == "user" and content.parts:
        for part in content.parts:
          if hasattr(part, "text") and part.text:
            return part.text
    return None

  def _extract_response_text(self, llm_response: LlmResponse) -> Optional[str]:
    """Extract text from the LLM response."""
    if not llm_response.content or not llm_response.content.parts:
      return None

    for part in llm_response.content.parts:
      if hasattr(part, "text") and part.text:
        return part.text
    return None

  async def before_model_callback(
      self,
      callback_context: CallbackContext,
      llm_request: LlmRequest,
  ) -> Optional[LlmResponse]:
    """Check cache before making LLM call.

    Args:
        callback_context: The callback context with session info.
        llm_request: The LLM request being made.

    Returns:
        LlmResponse if cache hit, None to proceed with LLM call.
    """
    if self._config.first_message_only and not self._is_first_message(
        callback_context
    ):
      logger.debug("Not first message, skipping cache check")
      return None

    prompt = self._extract_prompt(llm_request)
    if not prompt:
      logger.debug("No prompt found in request")
      return None

    cache_key = self._build_cache_key(prompt, callback_context)
    cache_entry = await self._provider.check(cache_key)

    if cache_entry:
      logger.info("Cache hit for prompt: %s", prompt[:50])
      return LlmResponse(
          content=types.Content(
              role="model",
              parts=[types.Part(text=cache_entry.response)],
          )
      )

    logger.debug("Cache miss for prompt: %s", prompt[:50])
    # Store prompt for after_model_callback
    session_key = self._get_session_key(callback_context)
    self._pending_prompts[session_key] = cache_key
    return None

  def _get_session_key(self, callback_context: CallbackContext) -> str:
    """Get a unique key for the current session context."""
    session = callback_context.session
    if session:
      return f"{session.app_name}:{session.user_id}:{session.id}"
    return "default"

  async def after_model_callback(
      self,
      callback_context: CallbackContext,
      llm_response: LlmResponse,
  ) -> Optional[LlmResponse]:
    """Store response in cache after LLM call.

    Args:
        callback_context: The callback context with session info.
        llm_response: The LLM response to cache.

    Returns:
        None to pass through the original response.
    """
    session_key = self._get_session_key(callback_context)
    cache_key = self._pending_prompts.pop(session_key, None)

    if not cache_key:
      logger.debug("No pending prompt for session, skipping cache store")
      return None

    # Don't cache error responses
    if llm_response.error_message:
      logger.debug("Response has error, skipping cache store")
      return None

    # Don't cache function call responses
    if llm_response.content and llm_response.content.parts:
      for part in llm_response.content.parts:
        if hasattr(part, "function_call") and part.function_call:
          logger.debug("Response is function call, skipping cache store")
          return None

    response_text = self._extract_response_text(llm_response)
    if not response_text:
      logger.debug("No text in response, skipping cache store")
      return None

    await self._provider.store(cache_key, response_text)
    logger.info("Cached response for prompt: %s", cache_key[:50])
    return None
