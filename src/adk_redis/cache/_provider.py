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
import importlib.metadata
import inspect
import logging
from typing import Any, Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr

logger = logging.getLogger(__name__)

# redisvl release that introduced the create_index flag on its extensions.
_CREATE_INDEX_MIN_REDISVL = "0.26.0"

# Keys per SCAN hint and per delete when clearing an externally managed
# cache index, matching the batch size RedisVL uses internally.
_CLEAR_BATCH_SIZE = 100

# Characters Redis reads as glob metacharacters in a SCAN MATCH pattern.
_GLOB_METACHARACTERS = frozenset("\\*?[]")


def _accepts_create_index(cache_cls: Any) -> bool:
  """Report whether a RedisVL cache class accepts the create_index flag.

  Args:
    cache_cls: The RedisVL cache class the provider is about to construct.

  Returns:
    True when the class accepts create_index, added in redisvl 0.26.0.
  """
  return "create_index" in inspect.signature(cache_cls).parameters


def _escape_glob(literal: str) -> str:
  """Escape Redis glob metacharacters so a pattern matches literally.

  A cache named "cache[ab]" would otherwise build the SCAN pattern
  "cache[ab]:*", which skips that cache's own keys and matches unrelated
  "cachea:" and "cacheb:" keys instead.

  Args:
    literal: The string to match literally.

  Returns:
    The string with every glob metacharacter backslash escaped.
  """
  return "".join(
      "\\" + char if char in _GLOB_METACHARACTERS else char for char in literal
  )


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
      entry ID; for RedisVLCacheProvider this is the RedisVL entry ID.
      It can be passed to delete_by_id() to retire exactly
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
    LangCacheProvider and RedisVLCacheProvider provide backend entry IDs;
    a backend that cannot provide an identifier must
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
  create_index: bool = Field(
      default=True,
      description=(
          "Whether RedisVL creates and validates the cache index. False"
          " attaches to an index provisioned outside adk-redis without"
          " verifying its schema. Requires"
          f" redisvl>={_CREATE_INDEX_MIN_REDISVL}."
      ),
  )
  overwrite: bool = Field(
      default=False,
      description=(
          "Whether to drop and recreate the index when it already exists."
          " Cannot be combined with create_index=False."
      ),
  )


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
    """Initialize the RedisVL cache provider.

    Args:
      config: Configuration for the cache and its index.
      vectorizer: RedisVL vectorizer used to embed prompts.

    Raises:
      ImportError: If redisvl is not installed.
      ValueError: If create_index is False on a redisvl older than 0.26.0,
        if create_index=False is combined with overwrite=True, or if an
        existing index's schema differs from this configuration.
      RedisSearchError: If RedisVL cannot manage the index, for instance
        when the credential is denied FT.INFO or FT.CREATE.
    """
    try:
      from redisvl.exceptions import RedisSearchError
      from redisvl.extensions.cache.llm import SemanticCache
    except ImportError as e:
      raise ImportError(
          "redisvl is required for RedisVLCacheProvider. "
          "Install it with: pip install redisvl>=0.18.2"
      ) from e

    self._config = config
    self._vectorizer = vectorizer

    # create_index is only forwarded when it is turned off, so the provider
    # keeps working against releases predating the flag.
    extra: dict[str, Any] = {}
    if not config.create_index:
      if not _accepts_create_index(SemanticCache):
        raise ValueError(
            "RedisVLCacheProviderConfig.create_index=False requires"
            f" redisvl>={_CREATE_INDEX_MIN_REDISVL}, found"
            f" {importlib.metadata.version('redisvl')}. Upgrade with: pip"
            f" install 'redisvl>={_CREATE_INDEX_MIN_REDISVL}', or leave"
            " create_index=True to have RedisVL create the index."
        )
      if config.overwrite:
        raise ValueError(
            "RedisVLCacheProviderConfig sets create_index=False together"
            " with overwrite=True. Set overwrite=False to attach to a"
            " pre-provisioned index, or create_index=True to let RedisVL"
            " own the index."
        )
      extra["create_index"] = False

    try:
      self._cache = SemanticCache(
          name=config.name,
          redis_url=config.redis_url,
          ttl=config.ttl,
          distance_threshold=config.distance_threshold,
          vectorizer=vectorizer,
          overwrite=config.overwrite,
          **extra,
      )
    except RedisSearchError as e:
      raise RedisSearchError(
          f"RedisVL could not manage the index {config.name!r}: {e}. If this"
          " credential is denied FT.INFO and FT.CREATE, set create_index="
          "False on RedisVLCacheProviderConfig to attach to an index"
          " provisioned elsewhere."
      ) from e
    except ValueError as e:
      # Only a schema mismatch is worth rewriting. Anything else, such as a
      # malformed redis_url, already names the field the caller must fix.
      if "schema does not match" not in str(e):
        raise
      raise ValueError(
          f"RedisVL rejected the existing index {config.name!r}: {e} Set"
          " overwrite=True on RedisVLCacheProviderConfig to rebuild it, or"
          " create_index=False to attach to it without validation."
      ) from e

  def _key_prefix(self) -> str:
    """Return the Redis key prefix RedisVL writes cache entries under.

    Returns:
      The prefix, which RedisVL derives from the cache name.
    """
    prefix: str = self._cache._get_prefix()
    return prefix

  async def check(self, prompt: str, **kwargs: Any) -> Optional[CacheEntry]:
    """Check for a semantically similar prompt in the cache.

    RedisVL refreshes each hit's TTL, so this issues EXPIRE alongside
    FT.SEARCH and needs write as well as read permissions.

    Args:
      prompt: The prompt to look up.
      **kwargs: Additional keyword arguments (unused).

    Returns:
      A CacheEntry on a hit, None on a miss. entry_id is the RedisVL entry
      ID of the matched entry and can be passed to delete_by_id().
    """
    result = await asyncio.to_thread(self._cache.check, prompt=prompt)
    if result:
      logger.debug("Cache hit for prompt: %s", prompt[:50])
      return CacheEntry(
          prompt=prompt,
          response=result[0]["response"],
          distance=result[0].get("vector_distance"),
          entry_id=result[0].get("entry_id"),
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
      The RedisVL entry ID of the newly written entry. It can be passed to
      delete_by_id() to retire exactly this entry.
    """
    key: str = await asyncio.to_thread(
        self._cache.store, prompt=prompt, response=response
    )
    entry_id = key.removeprefix(self._key_prefix())
    logger.debug("Stored response for prompt: %s", prompt[:50])
    return entry_id

  async def delete_by_id(self, entry_id: str, **kwargs: Any) -> None:
    """Delete exactly one cache entry by its RedisVL entry ID.

    Unlike clear(), which removes every entry, this drops only the entry
    identified by the RedisVL entry ID obtained from check() or store().

    Args:
      entry_id: The RedisVL entry ID of the entry to delete.
      **kwargs: Additional keyword arguments (unused).
    """
    await asyncio.to_thread(self._cache.drop, ids=[entry_id])
    logger.debug("Dropped cache entry: %s", entry_id)

  def _clear_external_index_entries(self) -> None:
    """Delete every cache entry key without touching the index.

    This mirrors RedisVL's own BaseCache.clear, which is a prefix scan and
    delete issuing no index command. RedisVL refuses that call on a cache
    whose index it does not manage, so the scan is repeated here, leaving
    the externally provisioned index in place.

    SCAN offers no snapshot, so an entry written by another process while
    this runs may survive.
    """
    client = self._cache._get_redis_client()
    pattern = f"{_escape_glob(self._key_prefix())}*"
    # Keys arrive as str or bytes depending on the client's decode setting.
    batch: list[Any] = []
    for key in client.scan_iter(match=pattern, count=_CLEAR_BATCH_SIZE):
      batch.append(key)
      if len(batch) >= _CLEAR_BATCH_SIZE:
        self._cache.drop(keys=batch)
        batch = []
    if batch:
      self._cache.drop(keys=batch)

  async def clear(self, **kwargs: Any) -> None:
    """Clear all entries from the cache, leaving the index in place.

    See _clear_external_index_entries() for the create_index=False path.
    For removing a single entry, use delete_by_id() instead.
    """
    if self._config.create_index:
      await asyncio.to_thread(self._cache.clear)
    else:
      await asyncio.to_thread(self._clear_external_index_entries)
    logger.info("Cache cleared")

  async def close(self) -> None:
    """Close the cache provider and release resources.

    RedisVL connects lazily, so a provider that issued no command yet holds
    no client. That is reachable when create_index is False, because
    construction sends nothing to Redis, and disconnect() tolerates it.

    ADK does not call this: a Runner knows nothing about objects reachable
    only through a callback, so the application owns the provider lifetime.
    """
    await asyncio.to_thread(self._cache.disconnect)
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
