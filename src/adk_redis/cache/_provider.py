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

"""Cache provider implementations for semantic caching."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Optional

from pydantic import BaseModel
from pydantic import Field

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
  """Represents a cached entry."""

  prompt: str
  response: str
  distance: Optional[float] = None
  metadata: Optional[dict[str, Any]] = None


class BaseCacheProvider(ABC):
  """Abstract base class for cache providers."""

  @abstractmethod
  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    """Check if a semantically similar prompt exists in the cache."""
    pass

  @abstractmethod
  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> None:
    """Store a prompt-response pair in the cache."""
    pass

  @abstractmethod
  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the cache."""
    pass

  @abstractmethod
  async def close(self) -> None:
    """Close the cache provider and release resources."""
    pass


class RedisVLCacheProviderConfig(BaseModel):
  """Configuration for RedisVL cache provider."""

  redis_url: str = Field(default="redis://localhost:6379")
  name: str = Field(default="adk_semantic_cache")
  ttl: int = Field(default=3600, ge=0)
  distance_threshold: float = Field(default=0.1, ge=0.0, le=2.0)


class RedisVLCacheProvider(BaseCacheProvider):
  """Cache provider using RedisVL's SemanticCache."""

  def __init__(self, config: RedisVLCacheProviderConfig, vectorizer: Any):
    """Initialize the RedisVL cache provider."""
    try:
      from redisvl.extensions.llmcache import SemanticCache
    except ImportError as e:
      raise ImportError(
          "redisvl is required for RedisVLCacheProvider. "
          "Install it with: pip install redisvl>=0.4.0"
      ) from e

    self._config = config
    self._vectorizer = vectorizer
    self._cache = SemanticCache(
        name=config.name,
        redis_url=config.redis_url,
        ttl=config.ttl,
        distance_threshold=config.distance_threshold,
        vectorizer=vectorizer,
        overwrite=True,  # Overwrite existing index if schema doesn't match
    )

  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    """Check for a semantically similar prompt in the cache."""
    result = await asyncio.to_thread(self._cache.check, prompt=prompt)
    if result:
      logger.debug("Cache hit for prompt: %s", prompt[:50])
      return CacheEntry(
          prompt=prompt,
          response=result[0]["response"],
          distance=result[0].get("vector_distance"),
      )
    logger.debug("Cache miss for prompt: %s", prompt[:50])
    return None

  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> None:
    """Store a prompt-response pair in the cache."""
    await asyncio.to_thread(self._cache.store, prompt=prompt, response=response)
    logger.debug("Stored response for prompt: %s", prompt[:50])

  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the cache."""
    await asyncio.to_thread(self._cache.clear)
    logger.info("Cache cleared")

  async def close(self) -> None:
    """Close the cache provider and release resources."""
    if hasattr(self._cache, "_index") and hasattr(self._cache._index, "client"):
      await asyncio.to_thread(self._cache._index.client.close)
    logger.debug("RedisVL cache provider closed")
