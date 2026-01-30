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

"""Base class for Redis Agent Memory tools."""

from __future__ import annotations

from functools import cached_property
import logging
from typing import Any

from google.adk.tools import BaseTool

from adk_redis.tools.memory._config import MemoryToolConfig

logger = logging.getLogger("adk_redis." + __name__)


class BaseMemoryTool(BaseTool):
  """Base class for all Redis Agent Memory tools.

  This class provides common functionality for memory tools:
  - Lazy initialization of the MemoryAPIClient
  - Shared configuration management
  - Standard error handling

  Subclasses should implement their specific tool logic using
  the `_client` property to access the Agent Memory Server.
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
        ImportError: If agent-memory-client package is not installed.
    """
    super().__init__(name=name, description=description)
    self._config = config

  def _get_client(self) -> Any:
    """Get a MemoryAPIClient instance.

    Note: We create a new client for each call instead of caching it because
    the ADK Runner creates a new event loop for each run() call, and cached
    async clients get tied to the first event loop and fail when it closes.

    Returns:
        An initialized MemoryAPIClient instance.

    Raises:
        ImportError: If agent-memory-client package is not installed.
    """
    try:
      from agent_memory_client import MemoryAPIClient
      from agent_memory_client import MemoryClientConfig
    except ImportError as e:
      raise ImportError(
          "agent-memory-client package is required for memory tools. "
          "Install it with: pip install adk-redis[memory]"
      ) from e

    client_config = MemoryClientConfig(
        base_url=self._config.api_base_url,
        timeout=self._config.timeout,
        default_namespace=self._config.default_namespace,
    )
    return MemoryAPIClient(client_config)

  def _build_recency_config(self) -> Any:
    """Build RecencyConfig from tool configuration.

    Returns:
        A RecencyConfig object for use with search operations.
    """
    from agent_memory_client.models import RecencyConfig

    return RecencyConfig(
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
    return user_id or self._config.default_user_id

