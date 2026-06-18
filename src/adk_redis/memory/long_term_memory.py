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

"""Redis long-term memory service for ADK."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from contextlib import asynccontextmanager
from functools import cached_property
from importlib import import_module
import logging
from typing import Any, AsyncIterator, Literal

from google.adk.events.event import Event
from google.adk.memory.base_memory_service import BaseMemoryService
from google.adk.memory.base_memory_service import SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session
from google.genai import types
from pydantic import BaseModel
from pydantic import Field
from typing_extensions import override

from adk_redis.memory._backends import MemoryBackendName
from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._backends import REDIS_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import extract_text_from_content
from adk_redis.memory._utils import extract_text_from_event
from adk_redis.memory._utils import read_field
from adk_redis.memory._utils import sanitize_managed_identifier
from adk_redis.memory._utils import stable_memory_id

logger = logging.getLogger("adk_redis." + __name__)

try:
  _agent_memory_client_module = import_module("agent_memory_client")
  _agent_memory_models_module = import_module("agent_memory_client.models")
except ImportError:
  _MemoryAPIClient: Any = None
  _MemoryClientConfig: Any = None
  _MemoryMessage: Any = None
  _MemoryStrategyConfig: Any = None
  _RecencyConfig: Any = None
  _WorkingMemory: Any = None
else:
  _MemoryAPIClient = _agent_memory_client_module.MemoryAPIClient
  _MemoryClientConfig = _agent_memory_client_module.MemoryClientConfig
  _MemoryMessage = _agent_memory_models_module.MemoryMessage
  _MemoryStrategyConfig = _agent_memory_models_module.MemoryStrategyConfig
  _RecencyConfig = _agent_memory_models_module.RecencyConfig
  _WorkingMemory = _agent_memory_models_module.WorkingMemory

try:
  _redis_agent_memory_module = import_module("redis_agent_memory")
except ImportError:
  _AgentMemory: Any = None
else:
  _AgentMemory = _redis_agent_memory_module.AgentMemory

MemoryTypeName = Literal["semantic", "episodic", "message"]


class RedisLongTermMemoryServiceConfig(BaseModel):
  """Configuration for Redis long-term memory.

  Attributes:
      backend: Memory backend to use.
      api_base_url: Memory API base URL.
      api_key: Redis Agent Memory API key.
      store_id: Redis Agent Memory store ID.
      timeout: HTTP timeout in seconds.
      timeout_ms: Optional SDK timeout in milliseconds.
      default_namespace: Default namespace for memory operations.
      search_top_k: Maximum number of memories to retrieve per search.
      similarity_threshold: Minimum similarity threshold for search results.
      distance_threshold: Backward-compatible alias for similarity_threshold.
      store_events_as_messages: Store ADK events as long-term message memories
        when add_session_to_memory or add_events_to_memory is called.
      default_memory_type: Default memory type for explicit add_memory writes.
      default_topics: Topics attached to created memory records.
      source: Source label used when building deterministic IDs.
      recency_boost: Backward-compatible option retained from the previous
        Agent Memory Server client.
      semantic_weight: Backward-compatible option retained from the previous
        Agent Memory Server client.
      recency_weight: Backward-compatible option retained from the previous
        Agent Memory Server client.
      freshness_weight: Backward-compatible option retained from the previous
        Agent Memory Server client.
      novelty_weight: Backward-compatible option retained from the previous
        Agent Memory Server client.
      half_life_last_access_days: Backward-compatible option retained from the
        previous Agent Memory Server client.
      half_life_created_days: Backward-compatible option retained from the
        previous Agent Memory Server client.
      extraction_strategy: Backward-compatible option retained from the
        previous Agent Memory Server client.
      extraction_strategy_config: Backward-compatible option retained from the
        previous Agent Memory Server client.
      model_name: Backward-compatible option retained from the previous Agent
        Memory Server client.
      context_window_max: Backward-compatible option retained from the
        previous Agent Memory Server client.
  """

  backend: MemoryBackendName = "redis-agent-memory"
  api_base_url: str = Field(default="http://localhost:8000")
  api_key: str | None = None
  store_id: str | None = None
  timeout: float = Field(default=30.0, gt=0.0)
  timeout_ms: int | None = Field(default=None, ge=1)
  default_namespace: str | None = None
  search_top_k: int = Field(default=10, ge=1)
  similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
  distance_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
  store_events_as_messages: bool = True
  default_memory_type: MemoryTypeName = "semantic"
  default_topics: list[str] = Field(default_factory=list)
  source: str = "adk-redis"
  recency_boost: bool = True
  semantic_weight: float = Field(default=0.8, ge=0.0, le=1.0)
  recency_weight: float = Field(default=0.2, ge=0.0, le=1.0)
  freshness_weight: float = Field(default=0.6, ge=0.0, le=1.0)
  novelty_weight: float = Field(default=0.4, ge=0.0, le=1.0)
  half_life_last_access_days: float = Field(default=7.0, gt=0.0)
  half_life_created_days: float = Field(default=30.0, gt=0.0)
  extraction_strategy: Literal[
      "discrete", "summary", "preferences", "custom"
  ] = "discrete"
  extraction_strategy_config: dict[str, Any] = Field(default_factory=dict)
  model_name: str | None = None
  context_window_max: int | None = Field(default=None, ge=1)


class RedisLongTermMemoryService(BaseMemoryService):
  """Long-term memory service backed by Redis memory backends.

  The service implements ADK's memory interface using either Redis Agent
  Memory or the self-hosted Agent Memory Server. Searches are scoped by user
  ID and namespace for both backends.

  Latest ADK versions add explicit `add_events_to_memory` and `add_memory`
  hooks. This service implements them while staying compatible with older ADK
  versions that only call `add_session_to_memory` and `search_memory`.
  """

  def __init__(self, config: RedisLongTermMemoryServiceConfig | None = None):
    """Initialize the Redis long-term memory service.

    Args:
        config: Configuration for the service. If None, defaults are used.
    """
    self._config = config or RedisLongTermMemoryServiceConfig()

  def _timeout_ms(self) -> int:
    """Return the configured SDK timeout in milliseconds."""
    return self._config.timeout_ms or int(self._config.timeout * 1000)

  def _get_client(self) -> Any:
    """Get a backend client for compatibility with existing tests."""
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      return self._get_agent_memory_server_client()
    return self._get_redis_agent_memory_client()

  def _get_redis_agent_memory_client(self) -> Any:
    """Get a Redis Agent Memory SDK client."""
    if _AgentMemory is None:
      raise ImportError(
          "redis-agent-memory package is required for "
          "RedisLongTermMemoryService. "
          "Install it with: pip install adk-redis[memory]"
      )

    return _AgentMemory(
        self._config.api_base_url,
        api_key=self._config.api_key,
        store_id=self._config.store_id,
        timeout_ms=self._timeout_ms(),
    )

  @cached_property
  def _agent_memory_server_client(self) -> Any:
    """Lazily initialize and return the self-hosted memory client."""
    if _MemoryAPIClient is None or _MemoryClientConfig is None:
      raise ImportError(
          "agent-memory-client package is required for the "
          "opensource-agent-memory backend. Install it with: "
          "pip install adk-redis[memory]"
      )

    client_config = _MemoryClientConfig(
        base_url=self._config.api_base_url,
        timeout=self._config.timeout,
        default_namespace=self._config.default_namespace,
        default_model_name=self._config.model_name,
        default_context_window_max=self._config.context_window_max,
    )
    return _MemoryAPIClient(client_config)

  def _get_agent_memory_server_client(self) -> Any:
    """Get the self-hosted Agent Memory Server client."""
    return self._agent_memory_server_client

  @asynccontextmanager
  async def _agent_memory(self) -> AsyncIterator[Any]:
    """Yield a Redis Agent Memory client and close SDK resources."""
    client = self._get_client()
    if hasattr(client, "__aenter__"):
      async with client as agent_memory:
        yield agent_memory
    else:
      yield client

  def _get_namespace(
      self,
      app_name: str,
      custom_metadata: Mapping[str, object] | None = None,
  ) -> str:
    """Get namespace from metadata, config, or app_name."""
    if custom_metadata:
      namespace = custom_metadata.get("namespace")
      if isinstance(namespace, str) and namespace:
        resolved = namespace
      else:
        resolved = self._config.default_namespace or app_name
    else:
      resolved = self._config.default_namespace or app_name

    if self._config.backend == REDIS_AGENT_MEMORY_BACKEND:
      return sanitize_managed_identifier(resolved)
    return resolved

  def _search_threshold(self) -> float | None:
    """Return the configured search threshold."""
    return (
        self._config.similarity_threshold
        if self._config.similarity_threshold is not None
        else self._config.distance_threshold
    )

  def _coerce_topics(
      self,
      *,
      app_name: str,
      custom_metadata: Mapping[str, object] | None = None,
      memory: MemoryEntry | None = None,
  ) -> list[str] | None:
    """Build topics for a memory record."""
    topics: list[str] = list(self._config.default_topics)
    metadata_values = []
    if custom_metadata:
      metadata_values.append(custom_metadata.get("topics"))
    if memory and memory.custom_metadata:
      metadata_values.append(memory.custom_metadata.get("topics"))

    for value in metadata_values:
      if isinstance(value, str):
        topics.append(value)
      elif isinstance(value, Sequence) and not isinstance(value, str):
        topics.extend(str(item) for item in value if item)

    if app_name not in topics:
      topics.append(app_name)
    return topics or None

  def _coerce_memory_type(
      self,
      value: object | None = None,
      *,
      default: MemoryTypeName | None = None,
  ) -> MemoryTypeName:
    """Normalize memory type aliases."""
    raw = str(value or default or self._config.default_memory_type).lower()
    memory_type_map = {
        "preference": "semantic",
        "fact": "semantic",
        "event": "episodic",
        "experience": "episodic",
        "conversation": "message",
    }
    memory_type = memory_type_map.get(raw, raw)
    if memory_type not in ("semantic", "episodic", "message"):
      return self._config.default_memory_type
    return memory_type  # type: ignore[return-value]

  def _memory_type_from_metadata(
      self,
      custom_metadata: Mapping[str, object] | None,
      memory: MemoryEntry | None = None,
      *,
      default: MemoryTypeName | None = None,
  ) -> MemoryTypeName:
    """Read memory type from metadata."""
    candidates = []
    if memory and memory.custom_metadata:
      candidates.append(memory.custom_metadata.get("memory_type"))
    if custom_metadata:
      candidates.append(custom_metadata.get("memory_type"))

    for candidate in candidates:
      if candidate:
        return self._coerce_memory_type(candidate, default=default)
    return self._coerce_memory_type(default=default)

  def _build_recency_config(self) -> Any:
    """Build RecencyConfig for the self-hosted memory backend."""
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

  def _build_agent_memory_server_working_memory(
      self,
      session: Session,
      custom_metadata: Mapping[str, object] | None = None,
  ) -> Any:
    """Convert an ADK session to self-hosted WorkingMemory."""
    if (
        _MemoryMessage is None
        or _MemoryStrategyConfig is None
        or _WorkingMemory is None
    ):
      raise ImportError(
          "agent-memory-client package is required for working memory. "
          "Install it with: pip install adk-redis[memory]"
      )

    messages = []
    for event in session.events:
      text = extract_text_from_event(event)
      if not text:
        continue
      role = "user" if event.author == "user" else "assistant"
      messages.append(_MemoryMessage(role=role, content=text))

    strategy_config = _MemoryStrategyConfig(
        strategy=self._config.extraction_strategy,
        config=self._config.extraction_strategy_config,
    )

    return _WorkingMemory(
        session_id=session.id,
        namespace=self._get_namespace(session.app_name, custom_metadata),
        user_id=session.user_id,
        messages=messages,
        long_term_memory_strategy=strategy_config,
    )

  async def _add_session_to_agent_memory_server(
      self,
      session: Session,
      custom_metadata: Mapping[str, object] | None = None,
  ) -> None:
    """Store a session in the self-hosted Agent Memory Server."""
    working_memory = self._build_agent_memory_server_working_memory(
        session,
        custom_metadata,
    )
    if not working_memory.messages:
      logger.debug("No messages to store for session %s", session.id)
      return

    response = await self._get_agent_memory_server_client().put_working_memory(
        session_id=session.id,
        memory=working_memory,
        user_id=session.user_id,
    )
    logger.info(
        "Stored %d messages for session %s (context: %.1f%% used)",
        len(working_memory.messages),
        session.id,
        getattr(response, "context_percentage_total_used", None) or 0,
    )

  async def _add_memory_to_agent_memory_server(
      self,
      *,
      app_name: str,
      user_id: str,
      memories: Sequence[MemoryEntry],
      custom_metadata: Mapping[str, object] | None,
  ) -> None:
    """Store explicit memories through the self-hosted memory API."""
    namespace = self._get_namespace(app_name, custom_metadata)
    client = self._get_agent_memory_server_client()

    for index, memory in enumerate(memories):
      text = extract_text_from_content(memory.content).strip()
      if not text:
        raise ValueError(f"memories[{index}] must include non-empty text")

      merged_metadata: dict[str, object] = {}
      if custom_metadata:
        merged_metadata.update(custom_metadata)
      if memory.custom_metadata:
        merged_metadata.update(memory.custom_metadata)

      session_id = str(
          merged_metadata.get("session_id")
          or stable_memory_id(
              self._config.source,
              "explicit",
              namespace,
              user_id,
              text,
          )
      )
      await client.add_memory_tool(
          session_id=session_id,
          text=text,
          memory_type=self._memory_type_from_metadata(
              custom_metadata,
              memory,
          ),
          topics=self._coerce_topics(
              app_name=app_name,
              custom_metadata=custom_metadata,
              memory=memory,
          ),
          namespace=namespace,
          user_id=user_id,
      )

  def _event_record_text(self, event: Event) -> str:
    """Build long-term message memory text for an ADK event."""
    text = extract_text_from_event(event).strip()
    if not text:
      return ""
    author = event.author or "agent"
    return f"{author}: {text}"

  def _build_event_records(
      self,
      *,
      app_name: str,
      user_id: str,
      events: Sequence[Event],
      session_id: str | None,
      custom_metadata: Mapping[str, object] | None,
  ) -> list[dict[str, Any]]:
    """Convert ADK events into Redis Agent Memory records."""
    namespace = self._get_namespace(app_name, custom_metadata)
    memory_type = self._memory_type_from_metadata(
        custom_metadata,
        default="message",
    )
    records = []

    for event in events:
      text = self._event_record_text(event)
      if not text:
        continue
      event_id = event.id or event.timestamp
      records.append(
          {
              "id": stable_memory_id(
                  self._config.source,
                  "event",
                  namespace,
                  user_id,
                  session_id or "",
                  event_id,
                  text,
              ),
              "text": text,
              "ownerId": user_id,
              "namespace": namespace,
              "sessionId": session_id,
              "topics": self._coerce_topics(
                  app_name=app_name,
                  custom_metadata=custom_metadata,
              ),
              "memoryType": memory_type,
          }
      )

    return records

  def _build_memory_records(
      self,
      *,
      app_name: str,
      user_id: str,
      memories: Sequence[MemoryEntry],
      custom_metadata: Mapping[str, object] | None,
  ) -> list[dict[str, Any]]:
    """Convert ADK MemoryEntry objects into Redis Agent Memory records."""
    namespace = self._get_namespace(app_name, custom_metadata)
    records = []

    for index, memory in enumerate(memories):
      text = extract_text_from_content(memory.content).strip()
      if not text:
        raise ValueError(f"memories[{index}] must include non-empty text")

      merged_metadata: dict[str, object] = {}
      if custom_metadata:
        merged_metadata.update(custom_metadata)
      if memory.custom_metadata:
        merged_metadata.update(memory.custom_metadata)

      session_id = merged_metadata.get("session_id")
      records.append(
          {
              "id": memory.id
              or stable_memory_id(
                  self._config.source,
                  "memory",
                  namespace,
                  user_id,
                  text,
              ),
              "text": text,
              "ownerId": user_id,
              "namespace": namespace,
              "sessionId": str(session_id) if session_id else None,
              "topics": self._coerce_topics(
                  app_name=app_name,
                  custom_metadata=custom_metadata,
                  memory=memory,
              ),
              "memoryType": self._memory_type_from_metadata(
                  custom_metadata,
                  memory,
              ),
          }
      )

    return records

  async def _bulk_create(self, records: list[dict[str, Any]]) -> None:
    """Create long-term memory records in Redis Agent Memory."""
    if not records:
      return
    async with self._agent_memory() as agent_memory:
      response = await agent_memory.bulk_create_long_term_memories_async(
          memories=records
      )
    errors = read_field(response, "errors")
    if errors:
      logger.warning("Redis Agent Memory reported write errors: %s", errors)

  @override
  async def add_session_to_memory(self, session: Session) -> None:
    """Add an ADK session to the configured long-term memory backend.

    Args:
        session: The ADK Session containing events to store.
    """
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      try:
        await self._add_session_to_agent_memory_server(session)
      except Exception as e:
        logger.error(
            "Failed to add session %s to memory: %s",
            session.id,
            e,
        )
      return

    await self.add_events_to_memory(
        app_name=session.app_name,
        user_id=session.user_id,
        events=session.events,
        session_id=session.id,
    )

  async def add_events_to_memory(
      self,
      *,
      app_name: str,
      user_id: str,
      events: Sequence[Event],
      session_id: str | None = None,
      custom_metadata: Mapping[str, object] | None = None,
  ) -> None:
    """Add ADK events to the configured memory backend."""
    if not self._config.store_events_as_messages:
      logger.debug("Event to memory storage is disabled")
      return

    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        session = Session(
            id=session_id
            or stable_memory_id(
                self._config.source,
                "events",
                app_name,
                user_id,
                *(getattr(event, "id", "") for event in events),
                *(getattr(event, "timestamp", "") for event in events),
            ),
            app_name=app_name,
            user_id=user_id,
            events=list(events),
        )
        await self._add_session_to_agent_memory_server(
            session,
            custom_metadata,
        )
        return

      records = self._build_event_records(
          app_name=app_name,
          user_id=user_id,
          events=events,
          session_id=session_id,
          custom_metadata=custom_metadata,
      )
      await self._bulk_create(records)
      logger.info("Stored %d event memory records", len(records))
    except Exception as e:
      logger.error("Failed to add events to memory: %s", e)

  async def add_memory(
      self,
      *,
      app_name: str,
      user_id: str,
      memories: Sequence[MemoryEntry],
      custom_metadata: Mapping[str, object] | None = None,
  ) -> None:
    """Add explicit durable memories to the configured backend."""
    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        await self._add_memory_to_agent_memory_server(
            app_name=app_name,
            user_id=user_id,
            memories=memories,
            custom_metadata=custom_metadata,
        )
        logger.info("Stored %d explicit memory records", len(memories))
        return

      records = self._build_memory_records(
          app_name=app_name,
          user_id=user_id,
          memories=memories,
          custom_metadata=custom_metadata,
      )
      await self._bulk_create(records)
      logger.info("Stored %d explicit memory records", len(records))
    except Exception as e:
      logger.error("Failed to add explicit memories: %s", e)

  def _coerce_memories(self, response: object) -> list[object]:
    """Coerce SDK search responses into a list of memory records."""
    if isinstance(response, dict):
      return list(response.get("items", response.get("memories", [])) or [])

    items = getattr(response, "items", None)
    if items is not None:
      return list(items)

    memories = getattr(response, "memories", None)
    return list(memories or [])

  def _memory_type_value(self, memory_type: object) -> str | None:
    """Return a JSON-friendly memory type."""
    if memory_type is None:
      return None
    return str(getattr(memory_type, "value", memory_type))

  async def _search_agent_memory_server(
      self, *, app_name: str, user_id: str, query: str
  ) -> SearchMemoryResponse:
    """Search memories through the self-hosted Agent Memory Server."""
    recency_config = (
        self._build_recency_config() if self._config.recency_boost else None
    )
    namespace = self._get_namespace(app_name)

    results = (
        await self._get_agent_memory_server_client().search_long_term_memory(
            text=query,
            namespace={"eq": namespace},
            user_id={"eq": user_id},
            distance_threshold=self._config.distance_threshold,
            recency=recency_config,
            limit=self._config.search_top_k,
        )
    )

    memories = []
    for record in getattr(results, "memories", []) or []:
      text = str(getattr(record, "text", "") or "")
      if not text:
        continue

      created_at = getattr(record, "created_at", None)
      timestamp = created_at.isoformat() if created_at else None
      content = types.Content(parts=[types.Part(text=text)])
      memories.append(
          MemoryEntry(
              id=getattr(record, "id", None),
              timestamp=timestamp,
              content=content,
              custom_metadata={
                  "namespace": getattr(record, "namespace", namespace),
                  "user_id": getattr(record, "user_id", user_id),
                  "session_id": getattr(record, "session_id", None),
                  "topics": getattr(record, "topics", []) or [],
                  "memory_type": getattr(record, "memory_type", None),
              },
          )
      )

    logger.info(
        "Found %d memories for query '%s' (namespace=%s, user=%s)",
        len(memories),
        query[:50],
        namespace,
        user_id,
    )
    return SearchMemoryResponse(memories=memories)

  @override
  async def search_memory(
      self, *, app_name: str, user_id: str, query: str
  ) -> SearchMemoryResponse:
    """Search for memories using the configured memory backend.

    Args:
        app_name: Application name, used as namespace if no default is set.
        user_id: Owner ID used to isolate memories.
        query: Search query for semantic matching.

    Returns:
        SearchMemoryResponse containing matching MemoryEntry objects.
    """
    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        return await self._search_agent_memory_server(
            app_name=app_name,
            user_id=user_id,
            query=query,
        )

      namespace = self._get_namespace(app_name)
      request: dict[str, Any] = {
          "text": query,
          "limit": self._config.search_top_k,
          "filter": {
              "ownerId": {"eq": user_id},
              "namespace": {"eq": namespace},
          },
          "filterOp": "all",
      }
      threshold = self._search_threshold()
      if threshold is not None:
        request["similarityThreshold"] = threshold

      async with self._agent_memory() as agent_memory:
        results = await agent_memory.search_long_term_memory_async(
            request=request
        )

      memories = []
      for record in self._coerce_memories(results):
        text = str(read_field(record, "text", "") or "")
        if not text:
          continue

        created_at = read_field(record, "created_at")
        timestamp = created_at.isoformat() if created_at else None
        memory_type = self._memory_type_value(read_field(record, "memory_type"))
        content = types.Content(parts=[types.Part(text=text)])
        memories.append(
            MemoryEntry(
                id=read_field(record, "id"),
                timestamp=timestamp,
                content=content,
                custom_metadata={
                    "namespace": read_field(record, "namespace"),
                    "owner_id": read_field(record, "owner_id"),
                    "session_id": read_field(record, "session_id"),
                    "topics": read_field(record, "topics", []) or [],
                    "memory_type": memory_type,
                },
            )
        )

      logger.info(
          "Found %d memories for query '%s' (namespace=%s, user=%s)",
          len(memories),
          query[:50],
          namespace,
          user_id,
      )
      return SearchMemoryResponse(memories=memories)

    except Exception as e:
      logger.error("Failed to search memories: %s", e)
      return SearchMemoryResponse(memories=[])

  async def close(self) -> None:
    """Close the memory service and cleanup resources."""
    if "_agent_memory_server_client" in self.__dict__:
      client = self.__dict__["_agent_memory_server_client"]
      close = getattr(client, "close", None)
      if close:
        await close()
      del self.__dict__["_agent_memory_server_client"]
