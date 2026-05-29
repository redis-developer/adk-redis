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

"""Configuration classes for Redis Agent Memory tools."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field

from adk_redis.memory._backends import MemoryBackendName


class MemoryToolConfig(BaseModel):
  """Shared configuration for all Redis memory tools.

  This configuration is used by all memory tools to connect to the
  configured memory backend and manage memory operations.

  Attributes:
      backend: Memory backend to use.
      api_base_url: Memory API base URL.
      api_key: Redis Agent Memory API key.
      store_id: Redis Agent Memory store ID.
      timeout: HTTP request timeout in seconds.
      timeout_ms: Optional SDK timeout in milliseconds.
      default_namespace: Default namespace for memory operations.
      default_user_id: Default user ID for memory operations (optional).
      default_owner_id: Default owner ID for memory operations (optional).
      search_top_k: Default maximum number of memories to retrieve.
      distance_threshold: Maximum distance threshold for search (0.0-1.0).
      recency_boost: Enable recency-aware re-ranking of search results.
      semantic_weight: Weight for semantic similarity (0.0-1.0).
      recency_weight: Weight for recency score (0.0-1.0).
      freshness_weight: Weight for freshness within recency score.
      novelty_weight: Weight for novelty within recency score.
      half_life_last_access_days: Half-life in days for last_accessed decay.
      half_life_created_days: Half-life in days for created_at decay.
      deduplicate: Enable deduplication when creating memories.

  Example:
      ```python
      from adk_redis.tools.memory import MemoryToolConfig

      config = MemoryToolConfig(
          api_base_url="http://localhost:8000",
          default_namespace="my_app",
          recency_boost=True,
      )
      ```
  """

  backend: MemoryBackendName = "redis-agent-memory"
  api_base_url: str = Field(default="http://localhost:8000")
  api_key: str | None = None
  store_id: str | None = None
  timeout: float = Field(default=30.0, gt=0.0)
  timeout_ms: int | None = Field(default=None, ge=1)
  default_namespace: str = Field(default="default")
  default_user_id: str | None = None
  default_owner_id: str | None = None
  search_top_k: int = Field(default=10, ge=1)
  distance_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
  recency_boost: bool = True
  semantic_weight: float = Field(default=0.8, ge=0.0, le=1.0)
  recency_weight: float = Field(default=0.2, ge=0.0, le=1.0)
  freshness_weight: float = Field(default=0.6, ge=0.0, le=1.0)
  novelty_weight: float = Field(default=0.4, ge=0.0, le=1.0)
  half_life_last_access_days: float = Field(default=7.0, gt=0.0)
  half_life_created_days: float = Field(default=30.0, gt=0.0)
  deduplicate: bool = True
