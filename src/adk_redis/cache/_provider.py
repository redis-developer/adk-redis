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
from pydantic import SecretStr

logger = logging.getLogger("adk_redis." + __name__)


@dataclass
class CacheEntry:
  """Represents a cached entry.

  Attributes:
    prompt: The prompt text that was matched.
    response: The cached response text.
    distance: The vector distance of the match, if available.
    metadata: Optional metadata stored alongside the entry.
    entry_id: Stable backend identifier for the matched entry, if the
      backend provides one. For LangCacheProvider this is the LangCache
      entry ID; for RedisVLCacheProvider this is the full Redis key of
      the entry. It can be passed to delete_by_id() to retire exactly
      this entry. None when the backend does not expose an identifier.
  """

  prompt: str
  response: str
  distance: Optional[float] = None
  metadata: Optional[dict[str, Any]] = None
  entry_id: Optional[str] = None


class BaseCacheProvider(ABC):
  """Abstract base class for cache providers.

  Entry identity contract:
    Providers surface a stable per-entry identifier when the backend
    exposes one. check() populates CacheEntry.entry_id on hits and
    store() returns the identifier of the newly written entry. Both
    LangCacheProvider (LangCache entry IDs) and RedisVLCacheProvider
    (full Redis keys) provide identifiers; a backend that cannot must
    leave CacheEntry.entry_id as None and return None from store().
    Identifiers from check() and store() are interchangeable inputs to
    delete_by_id() for the same provider instance.
  """

  @abstractmethod
  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    """Check if a semantically similar prompt exists in the cache.

    Args:
      prompt: The prompt to look up.
      **kwargs: Provider-specific options.

    Returns:
      A CacheEntry on a hit (with entry_id populated when the backend
      provides one), None on a miss.
    """
    pass

  @abstractmethod
  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> Optional[str]:
    """Store a prompt-response pair in the cache.

    Args:
      prompt: The prompt text.
      response: The response text.
      metadata: Optional metadata to store alongside the entry.
      **kwargs: Provider-specific options.

    Returns:
      The identifier of the newly written entry when the backend
      provides one, otherwise None. The identifier can be passed to
      delete_by_id() to retire exactly this entry.
    """
    pass

  @abstractmethod
  async def delete_by_id(self, entry_id: str, **kwargs: Any) -> None:
    """Delete exactly one entry from the cache by its identifier.

    Unlike clear(), which removes every entry in the cache, this targets
    a single entry, identified by the entry_id obtained from check() or
    store(). Deleting an identifier that no longer exists is a no-op.

    Args:
      entry_id: The identifier of the entry to delete, as returned by
        check() (CacheEntry.entry_id) or store() on this provider.
      **kwargs: Provider-specific options.
    """
    pass

  @abstractmethod
  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the cache.

    For removing a single entry, use delete_by_id() instead.
    """
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


class LangCacheProviderConfig(BaseModel):
  """Configuration for LangCache (managed semantic cache) provider.

  LangCache is a managed semantic caching service provided by Redis.
  It requires a cache_id and api_key from the LangCache service.
  """

  name: str = Field(default="langcache")
  server_url: str = Field(
      default="https://aws-us-east-1.langcache.redis.io",
      description="LangCache server URL.",
  )
  cache_id: str = Field(
      ...,
      min_length=1,
      description="LangCache cache ID from the LangCache service.",
  )
  api_key: SecretStr = Field(
      ...,
      min_length=1,
      description="LangCache API key for authentication.",
  )
  ttl: Optional[int] = Field(
      default=None,
      ge=0,
      description="TTL in seconds for cached entries. None means no expiry.",
  )
  distance_threshold: Optional[float] = Field(
      default=None,
      ge=0.0,
      le=2.0,
      description="Distance threshold for semantic similarity matching.",
  )
  use_exact_search: bool = Field(
      default=True,
      description="Whether to use exact (hash-based) search.",
  )
  use_semantic_search: bool = Field(
      default=True,
      description="Whether to use semantic (vector-based) search.",
  )


class RedisVLCacheProvider(BaseCacheProvider):
  """Cache provider using RedisVL's SemanticCache."""

  def __init__(self, config: RedisVLCacheProviderConfig, vectorizer: Any):
    """Initialize the RedisVL cache provider."""
    try:
      from redisvl.extensions.cache.llm import SemanticCache
    except ImportError as e:
      raise ImportError(
          "redisvl is required for RedisVLCacheProvider. "
          "Install it with: pip install redisvl>=0.18.2"
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
    """Check for a semantically similar prompt in the cache.

    Args:
      prompt: The prompt to look up.
      **kwargs: Additional keyword arguments (unused).

    Returns:
      A CacheEntry on a hit, None on a miss. entry_id is the full Redis
      key of the matched entry and can be passed to delete_by_id().
    """
    result = await asyncio.to_thread(self._cache.check, prompt=prompt)
    if result:
      logger.debug("Cache hit for prompt: %s", prompt[:50])
      return CacheEntry(
          prompt=prompt,
          response=result[0]["response"],
          distance=result[0].get("vector_distance"),
          entry_id=result[0].get("key"),
      )
    logger.debug("Cache miss for prompt: %s", prompt[:50])
    return None

  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> Optional[str]:
    """Store a prompt-response pair in the cache.

    Args:
      prompt: The prompt text.
      response: The response text.
      metadata: Optional metadata (unused by this provider).
      **kwargs: Additional keyword arguments (unused).

    Returns:
      The full Redis key of the newly written entry. It can be passed
      to delete_by_id() to retire exactly this entry.
    """
    key: str = await asyncio.to_thread(
        self._cache.store, prompt=prompt, response=response
    )
    logger.debug("Stored response for prompt: %s", prompt[:50])
    return key

  async def delete_by_id(self, entry_id: str, **kwargs: Any) -> None:
    """Delete exactly one cache entry by its Redis key.

    Unlike clear(), which removes every entry, this drops only the entry
    identified by the full Redis key obtained from check() or store().

    Args:
      entry_id: The full Redis key of the entry to delete.
      **kwargs: Additional keyword arguments (unused).
    """
    await asyncio.to_thread(self._cache.drop, keys=[entry_id])
    logger.debug("Dropped cache entry: %s", entry_id)

  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the cache.

    For removing a single entry, use delete_by_id() instead.
    """
    await asyncio.to_thread(self._cache.clear)
    logger.info("Cache cleared")

  async def close(self) -> None:
    """Close the cache provider and release resources."""
    if hasattr(self._cache, "_index") and hasattr(self._cache._index, "client"):
      await asyncio.to_thread(self._cache._index.client.close)
    logger.debug("RedisVL cache provider closed")


class LangCacheProvider(BaseCacheProvider):
  """Cache provider using Redis LangCache (managed semantic cache service).

  LangCache is a managed semantic caching service that handles embedding
  generation, storage, and retrieval. Unlike RedisVLCacheProvider, it does
  not require a local vectorizer; embeddings are handled server-side.

  Requires redisvl>=0.11.1 with LangCache support.
  """

  def __init__(self, config: LangCacheProviderConfig):
    """Initialize the LangCache cache provider.

    Args:
      config: Configuration for the LangCache provider.

    Raises:
      ImportError: If redisvl>=0.11.1 is not installed.
    """
    try:
      from redisvl.extensions.cache.llm import LangCacheSemanticCache
    except ImportError as e:
      raise ImportError(
          "redisvl>=0.11.1 with LangCache support is required for "
          "LangCacheProvider. Install it with: "
          "pip install 'adk-redis[langcache]'"
      ) from e

    self._config = config
    self._cache = LangCacheSemanticCache(
        name=config.name,
        server_url=config.server_url,
        cache_id=config.cache_id,
        api_key=config.api_key.get_secret_value(),
        ttl=config.ttl,
        use_exact_search=config.use_exact_search,
        use_semantic_search=config.use_semantic_search,
        distance_scale="redis",
    )

  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    """Check for a semantically similar prompt in LangCache.

    Args:
      prompt: The prompt to check.
      **kwargs: Additional keyword arguments (e.g., distance_threshold).

    Returns:
      A CacheEntry if a cache hit is found, None otherwise. entry_id is
      the LangCache entry ID of the matched entry and can be passed to
      delete_by_id().
    """
    distance_threshold = kwargs.get(
        "distance_threshold", self._config.distance_threshold
    )
    acheck_kwargs: dict[str, Any] = {"prompt": prompt}
    if distance_threshold is not None:
      acheck_kwargs["distance_threshold"] = distance_threshold
    result = await self._cache.acheck(**acheck_kwargs)
    if result:
      logger.debug("LangCache hit for prompt: %s", prompt[:50])
      return CacheEntry(
          prompt=prompt,
          response=result[0]["response"],
          distance=result[0].get("vector_distance"),
          metadata=result[0].get("metadata"),
          entry_id=result[0].get("entry_id"),
      )
    logger.debug("LangCache miss for prompt: %s", prompt[:50])
    return None

  async def store(
      self,
      prompt: str,
      response: str,
      metadata: Optional[dict[str, Any]] = None,
      **kwargs: Any,
  ) -> Optional[str]:
    """Store a prompt-response pair in LangCache.

    Args:
      prompt: The prompt text.
      response: The response text.
      metadata: Optional metadata to store alongside the entry.
      **kwargs: Additional keyword arguments (e.g., ttl).

    Returns:
      The LangCache entry ID of the newly written entry. It can be
      passed to delete_by_id() to retire exactly this entry.
    """
    astore_kwargs: dict[str, Any] = {
        "prompt": prompt,
        "response": response,
        "metadata": metadata,
    }
    # Only override TTL when an explicit, non-None value is provided.
    ttl = kwargs.get("ttl")
    if ttl is not None:
      astore_kwargs["ttl"] = ttl
    entry_id = await self._cache.astore(**astore_kwargs)
    logger.debug("LangCache stored response for prompt: %s", prompt[:50])
    return entry_id or None

  async def delete_by_id(self, entry_id: str, **kwargs: Any) -> None:
    """Delete exactly one LangCache entry by its entry ID.

    Unlike clear(), which removes every entry, this deletes only the
    entry identified by the LangCache entry ID obtained from check()
    or store().

    Args:
      entry_id: The LangCache entry ID of the entry to delete.
      **kwargs: Additional keyword arguments (unused).
    """
    await self._cache.adelete_by_id(entry_id)
    logger.debug("LangCache deleted entry: %s", entry_id)

  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the LangCache.

    For removing a single entry, use delete_by_id() instead.
    """
    await self._cache.aclear()
    logger.info("LangCache cleared")

  async def close(self) -> None:
    """Close the LangCache provider and release resources."""
    await self._cache.adisconnect()
    logger.debug("LangCache provider closed")
