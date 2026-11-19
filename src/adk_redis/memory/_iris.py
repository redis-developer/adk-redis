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

"""Managed memory connections through the Redis Iris SDK."""

from importlib import import_module
import os
from types import ModuleType
from typing import Any

iris_memory: ModuleType | None
try:
  iris_memory = import_module("redis_iris.agent_memory")
except ModuleNotFoundError as exc:
  if exc.name != "redis_iris":
    raise
  iris_memory = None


def managed_store_id(store_id: str | None) -> str | None:
  """Resolve the store used by the client and the namespace cache."""
  return (
      store_id
      or os.getenv("IRIS_AGENT_MEMORY_STORE_ID")
      or os.getenv("AGENT_MEMORY_STORE_ID")
  )


def connect_managed_memory(
    *,
    url: str,
    api_key: str | None,
    store_id: str | None,
    timeout: float,
    timeout_ms: int | None,
) -> Any:
  """Open a fresh Iris client for the current event loop."""
  if iris_memory is None:
    raise ImportError(
        "Managed memory requires Python 3.11+ and redis-iris. "
        "Install it with: pip install 'adk-redis[memory]'"
    )
  settings = iris_memory.AgentMemorySettings(
      url=url,
      api_key=api_key
      or os.getenv("IRIS_AGENT_MEMORY_API_KEY")
      or os.getenv("AGENT_MEMORY_API_KEY"),
      store_id=managed_store_id(store_id),
      timeout=timeout if timeout_ms is None else timeout_ms / 1000,
  )
  return iris_memory.connect(settings)
