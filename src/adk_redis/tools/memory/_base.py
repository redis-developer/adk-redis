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

"""Base class for Redis memory tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from importlib import import_module
import logging
from typing import Any, AsyncIterator

from google.adk.tools.base_tool import BaseTool

from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)

try:
  _agent_memory_client_module = import_module("agent_memory_client")
  _agent_memory_models_module = import_module("agent_memory_client.models")
except ImportError:
  _MemoryAPIClient: Any = None
  _MemoryClientConfig: Any = None
  _RecencyConfig: Any = None
else:
  _MemoryAPIClient = _agent_memory_client_module.MemoryAPIClient
  _MemoryClientConfig = _agent_memory_client_module.MemoryClientConfig
  _RecencyConfig = _agent_memory_models_module.RecencyConfig

try:
  _redis_agent_memory_module = import_module("redis_agent_memory")
except ImportError:
  _AgentMemory: Any = None
else:
  _AgentMemory = _redis_agent_memory_module.AgentMemory


class BaseMemoryTool(BaseTool):
  """Base class for all Redis memory tools.

  This class provides common functionality for memory tools:
  - Lazy initialization of memory backend clients
  - Shared configuration management
  - Standard error handling

  Subclasses should implement their specific tool logic using
  the configured backend helpers.
  """

  def __init__(
      self,
      *,
      config: MemoryToolConfig,
      name: str,
      description: str,
  ):
    """Initialize the base memory tool.

    Args:
        config: Configuration for connecting to Agent Memory Server.
        name: The name of the tool (exposed to LLM).
        description: The description of the tool (exposed to LLM).

    Raises:
        ImportError: If the configured backend package is not installed.
    """
    super().__init__(name=name, description=description)
    self._config = config

  def _get_client(self) -> Any:
    """Get a backend client for compatibility with existing tests."""
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      return self._get_agent_memory_server_client()
    return self._get_redis_agent_memory_client()

  def _get_redis_agent_memory_client(self) -> Any:
    """Get a Redis Agent Memory SDK client.

    Note: We create a new client for each call instead of caching it because
    the ADK Runner creates a new event loop for each run() call, and cached
    async clients get tied to the first event loop and fail when it closes.

    Returns:
        An initialized Redis Agent Memory SDK client.

    Raises:
        ImportError: If redis-agent-memory package is not installed.
    """
    if _AgentMemory is None:
      raise ImportError(
          "redis-agent-memory package is required for memory tools. "
          "Install it with: pip install adk-redis[memory]"
      )

    return _AgentMemory(
        self._config.api_base_url,
        api_key=self._config.api_key,
        store_id=self._config.store_id,
        timeout_ms=self._timeout_ms(),
    )

  def _get_agent_memory_server_client(self) -> Any:
    """Get a self-hosted Agent Memory Server client."""
    if _MemoryAPIClient is None or _MemoryClientConfig is None:
      raise ImportError(
          "agent-memory-client package is required for memory tools with "
          "backend='opensource-agent-memory'. Install it with: "
          "pip install adk-redis[memory]"
      )

    client_config = _MemoryClientConfig(
        base_url=self._config.api_base_url,
        timeout=self._config.timeout,
        default_namespace=self._config.default_namespace,
    )
    return _MemoryAPIClient(client_config)

  def _timeout_ms(self) -> int:
    """Return the configured SDK timeout in milliseconds."""
    return self._config.timeout_ms or int(self._config.timeout * 1000)

  @asynccontextmanager
  async def _agent_memory(self) -> AsyncIterator[Any]:
    """Yield a Redis Agent Memory client and close SDK resources."""
    client = self._get_client()
    if hasattr(client, "__aenter__"):
      async with client as agent_memory:
        yield agent_memory
    else:
      yield client

  def _build_recency_config(self) -> Any:
    """Build RecencyConfig from tool configuration.

    Returns:
        A RecencyConfig object for the self-hosted backend, or None for
        Redis Agent Memory.
    """
    if self._config.backend != OPENSOURCE_AGENT_MEMORY_BACKEND:
      return None

    if _RecencyConfig is None:
      raise ImportError(
          "agent-memory-client package is required for recency search. "
          "Install it with: pip install adk-redis[memory]"
      )

    return _RecencyConfig(
        recency_boost=self._config.recency_boost,
        semantic_weight=self._config.semantic_weight,
        recency_weight=self._config.recency_weight,
        freshness_weight=self._config.freshness_weight,
        novelty_weight=self._config.novelty_weight,
        half_life_last_access_days=self._config.half_life_last_access_days,
        half_life_created_days=self._config.half_life_created_days,
    )

  def _get_namespace(self, namespace: str | None = None) -> str:
    """Get the namespace to use for operations.

    Args:
        namespace: Optional namespace override.

    Returns:
        The namespace to use (override or default).
    """
    return namespace or self._config.default_namespace

  def _get_user_id(self, user_id: str | None = None) -> str | None:
    """Get the user ID to use for operations.

    Args:
        user_id: Optional user ID override.

    Returns:
        The user ID to use (override or default).
    """
    return (
        user_id or self._config.default_owner_id or self._config.default_user_id
    )
