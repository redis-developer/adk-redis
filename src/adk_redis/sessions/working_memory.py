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

"""Redis working memory session service for ADK."""

from __future__ import annotations

import base64
from contextlib import asynccontextmanager
import hashlib
from importlib import import_module
import logging
import time
from typing import Any, AsyncIterator, Literal
import uuid

from google.adk.events.event import Event
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.base_session_service import GetSessionConfig
from google.adk.sessions.base_session_service import ListSessionsResponse
from google.adk.sessions.session import Session
from google.genai import types
from pydantic import BaseModel
from pydantic import Field
from typing_extensions import override

from adk_redis.memory._backends import MemoryBackendName
from adk_redis.memory._backends import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis.memory._backends import REDIS_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import extract_text_from_event
from adk_redis.memory._utils import is_not_found_error
from adk_redis.memory._utils import read_field
from adk_redis.memory._utils import sanitize_managed_identifier
from adk_redis.memory._utils import timestamp_to_datetime

logger = logging.getLogger("adk_redis." + __name__)

_SESSION_ID_PREFIX = "adkredis"
_MANAGED_SESSION_ID_LEN = 64

try:
  _agent_memory_client_module = import_module("agent_memory_client")
  _agent_memory_exceptions_module = import_module(
      "agent_memory_client.exceptions"
  )
  _agent_memory_models_module = import_module("agent_memory_client.models")
except ImportError:
  _MemoryAPIClient: Any = None
  _MemoryClientConfig: Any = None

  class _FallbackMemoryNotFoundError(Exception):
    """Fallback used when agent-memory-client is not installed."""

  _MemoryNotFoundError: Any = _FallbackMemoryNotFoundError
  _MemoryMessage: Any = None
  _MemoryStrategyConfig: Any = None
else:
  _MemoryAPIClient = _agent_memory_client_module.MemoryAPIClient
  _MemoryClientConfig = _agent_memory_client_module.MemoryClientConfig
  _MemoryNotFoundError = _agent_memory_exceptions_module.MemoryNotFoundError
  _MemoryMessage = _agent_memory_models_module.MemoryMessage
  _MemoryStrategyConfig = _agent_memory_models_module.MemoryStrategyConfig

try:
  _redis_agent_memory_module = import_module("redis_agent_memory")
except ImportError:
  _AgentMemory: Any = None
else:
  _AgentMemory = _redis_agent_memory_module.AgentMemory


class RedisWorkingMemorySessionServiceConfig(BaseModel):
  """Configuration for Redis working memory session service.

  Attributes:
      backend: Memory backend to use.
      api_base_url: Memory API base URL.
      api_key: Redis Agent Memory API key.
      store_id: Redis Agent Memory store ID.
      timeout: HTTP request timeout in seconds.
      timeout_ms: Optional SDK timeout in milliseconds.
      default_namespace: Default namespace for session isolation.
      model_name: Backward-compatible option retained from the previous client.
      context_window_max: Backward-compatible option retained from the
        previous client.
      extraction_strategy: Backward-compatible option retained from the
        previous client.
      extraction_strategy_config: Backward-compatible option retained from the
        previous client.
      session_ttl_seconds: Backward-compatible option retained from the
        previous client.
  """

  backend: MemoryBackendName = "redis-agent-memory"
  api_base_url: str = Field(default="http://localhost:8000")
  api_key: str | None = None
  store_id: str | None = None
  timeout: float = Field(default=30.0, gt=0.0)
  timeout_ms: int | None = Field(default=None, ge=1)
  default_namespace: str | None = None
  model_name: str | None = None
  context_window_max: int | None = Field(default=None, ge=1)
  extraction_strategy: Literal[
      "discrete", "summary", "preferences", "custom"
  ] = "discrete"
  extraction_strategy_config: dict[str, Any] = Field(default_factory=dict)
  session_ttl_seconds: int | None = Field(default=None, ge=1)


class RedisWorkingMemorySessionService(BaseSessionService):
  """Session service backed by Redis memory backends.

  Redis Agent Memory stores session events by session ID. The self-hosted
  Agent Memory Server stores sessions in Working Memory. Returned ADK
  sessions keep the original caller-facing session ID for both backends.
  """

  def __init__(
      self, config: RedisWorkingMemorySessionServiceConfig | None = None
  ):
    """Initialize the Redis Agent Memory session service.

    Args:
        config: Configuration for the service. If None, defaults are used.
    """
    self._config = config or RedisWorkingMemorySessionServiceConfig()

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
          "RedisWorkingMemorySessionService. "
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

  @asynccontextmanager
  async def _agent_memory(self) -> AsyncIterator[Any]:
    """Yield a Redis Agent Memory client and close SDK resources."""
    client = self._get_client()
    if hasattr(client, "__aenter__"):
      async with client as agent_memory:
        yield agent_memory
    else:
      yield client

  def _get_namespace(self, app_name: str) -> str:
    """Get namespace from config or app_name."""
    namespace = self._config.default_namespace or app_name
    if self._config.backend == REDIS_AGENT_MEMORY_BACKEND:
      return sanitize_managed_identifier(namespace)
    return namespace

  def _encode_segment(self, value: str) -> str:
    """Encode one storage session ID segment."""
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")

  def _decode_segment(self, value: str) -> str:
    """Decode one storage session ID segment."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")

  def _storage_session_id(
      self, *, app_name: str, user_id: str, session_id: str
  ) -> str:
    """Build a managed Redis Agent Memory session ID.

    Managed session IDs must be 1-64 chars and contain only alphanumeric
    characters and hyphens. Encode ADK scope as a deterministic SHA-256 hex
    digest so UUID session IDs and namespaces remain isolated per store.
    """
    namespace = self._get_namespace(app_name)
    return hashlib.sha256(
        f"{namespace}\0{user_id}\0{session_id}".encode("utf-8")
    ).hexdigest()[:_MANAGED_SESSION_ID_LEN]

  def _session_scope_from_response(
      self, response: object
  ) -> tuple[str, str, str] | None:
    """Extract ADK session scope from a Redis Agent Memory session response."""
    for redis_event in read_field(response, "events", []) or []:
      metadata = read_field(redis_event, "metadata", {}) or {}
      namespace = metadata.get("namespace")
      stored_user_id = metadata.get("user_id")
      adk_session_id = metadata.get("adk_session_id")
      if namespace and stored_user_id and adk_session_id:
        return (
            str(namespace),
            str(stored_user_id),
            str(adk_session_id),
        )
    return None

  def _parse_storage_session_id(
      self, storage_session_id: str
  ) -> tuple[str, str, str] | None:
    """Parse an internal storage session ID.

    Returns:
        Tuple of namespace, user_id, and ADK session_id, or None.
    """
    parts = storage_session_id.split(":")
    if len(parts) != 4 or parts[0] != _SESSION_ID_PREFIX:
      return None

    try:
      return (
          self._decode_segment(parts[1]),
          self._decode_segment(parts[2]),
          self._decode_segment(parts[3]),
      )
    except Exception:
      return None

  def _event_role(self, event: Event) -> Any:
    """Map an ADK event to a Redis Agent Memory role."""
    content_role = event.content.role if event.content else None
    if event.author == "user" or content_role == "user":
      return "USER"
    if content_role == "system":
      return "SYSTEM"
    return "ASSISTANT"

  def _event_metadata(
      self,
      *,
      event: Event,
      app_name: str,
      user_id: str,
      session_id: str,
  ) -> dict[str, Any]:
    """Build portable metadata for an ADK event."""
    metadata: dict[str, Any] = {
        "source": "adk-redis",
        "namespace": self._get_namespace(app_name),
        "app_name": app_name,
        "user_id": user_id,
        "adk_session_id": session_id,
        "adk_event_id": event.id,
        "adk_author": event.author,
    }
    if event.actions and event.actions.state_delta:
      metadata["state_delta"] = dict(event.actions.state_delta)
    return metadata

  def _event_actor_id(self, session: Session, event: Event) -> str:
    """Return the Redis actor ID for an ADK event."""
    if event.author == "user":
      actor_id = session.user_id
    else:
      actor_id = event.author or session.app_name
    if self._config.backend == REDIS_AGENT_MEMORY_BACKEND:
      return sanitize_managed_identifier(actor_id)
    return actor_id

  def _build_agent_memory_server_strategy(self) -> Any:
    """Build the self-hosted memory extraction strategy config."""
    if _MemoryStrategyConfig is None:
      raise ImportError(
          "agent-memory-client package is required for memory strategies. "
          "Install it with: pip install adk-redis[memory]"
      )

    return _MemoryStrategyConfig(
        strategy=self._config.extraction_strategy,
        config=self._config.extraction_strategy_config,
    )

  def _event_to_agent_memory_server_message(self, event: Event) -> Any:
    """Convert an ADK event to a self-hosted memory message."""
    if _MemoryMessage is None:
      raise ImportError(
          "agent-memory-client package is required for memory messages. "
          "Install it with: pip install adk-redis[memory]"
      )

    text = extract_text_from_event(event)
    if not text:
      return None

    role = "user" if event.author == "user" else "assistant"
    return _MemoryMessage(
        role=role,
        content=text,
        created_at=timestamp_to_datetime(event.timestamp),
    )

  def _agent_memory_server_response_to_session(
      self,
      response: Any,
      app_name: str,
      user_id: str,
  ) -> Session:
    """Convert a self-hosted WorkingMemory response to an ADK Session."""
    events = []
    for message in getattr(response, "messages", None) or []:
      role_raw = getattr(message, "role", "")
      author = "user" if role_raw == "user" else app_name
      content_role = "user" if role_raw == "user" else "model"
      content = types.Content(
          role=content_role,
          parts=[types.Part(text=getattr(message, "content", ""))],
      )
      created_at = getattr(message, "created_at", None)
      timestamp = created_at.timestamp() if created_at else time.time()
      events.append(
          Event(
              author=author,
              content=content,
              timestamp=timestamp,
          )
      )

    return Session(
        id=getattr(response, "session_id"),
        app_name=app_name,
        user_id=user_id,
        events=events,
        state=getattr(response, "data", None) or {},
        last_update_time=time.time(),
    )

  async def _create_session_agent_memory_server(
      self,
      *,
      app_name: str,
      user_id: str,
      state: dict[str, Any] | None,
      session_id: str | None,
  ) -> Session:
    """Create a session in the self-hosted Agent Memory Server."""
    session_id = (
        session_id.strip()
        if session_id and session_id.strip()
        else str(uuid.uuid4())
    )
    namespace = self._get_namespace(app_name)
    client = self._get_agent_memory_server_client()

    created, working_memory = await client.get_or_create_working_memory(
        session_id=session_id,
        namespace=namespace,
        user_id=user_id,
        long_term_memory_strategy=self._build_agent_memory_server_strategy(),
    )

    if not created:
      logger.warning(
          "Session %s already exists in namespace %s, returning existing",
          session_id,
          namespace,
      )
      return self._agent_memory_server_response_to_session(
          working_memory,
          app_name,
          user_id,
      )

    if state or self._config.session_ttl_seconds:
      if state:
        working_memory.data = state
      if self._config.session_ttl_seconds:
        working_memory.ttl_seconds = self._config.session_ttl_seconds
      await client.put_working_memory(
          session_id=session_id,
          memory=working_memory,
          user_id=user_id,
      )

    logger.info("Created session %s in namespace %s", session_id, namespace)
    return Session(
        id=session_id,
        app_name=app_name,
        user_id=user_id,
        state=state or {},
        events=[],
        last_update_time=time.time(),
    )

  async def _get_session_agent_memory_server(
      self,
      *,
      app_name: str,
      user_id: str,
      session_id: str,
      config: GetSessionConfig | None,
  ) -> Session | None:
    """Retrieve a session from the self-hosted Agent Memory Server."""
    try:
      namespace = self._get_namespace(app_name)
      client = self._get_agent_memory_server_client()
      _, response = await client.get_or_create_working_memory(
          session_id=session_id,
          namespace=namespace,
          user_id=user_id,
          model_name=self._config.model_name,
          context_window_max=self._config.context_window_max,
      )
      session = self._agent_memory_server_response_to_session(
          response,
          app_name,
          user_id,
      )

      if config:
        if config.num_recent_events is not None:
          session.events = session.events[-config.num_recent_events :]
        if config.after_timestamp is not None:
          session.events = [
              event
              for event in session.events
              if event.timestamp >= config.after_timestamp
          ]

      return session

    except _MemoryNotFoundError:
      return None
    except Exception as e:
      logger.error("Failed to get session %s: %s", session_id, e)
      return None

  async def _list_sessions_agent_memory_server(
      self, *, app_name: str, user_id: str | None
  ) -> ListSessionsResponse:
    """List sessions from the self-hosted Agent Memory Server."""
    if user_id is None:
      raise ValueError(
          "user_id is required for RedisWorkingMemorySessionService"
      )

    try:
      namespace = self._get_namespace(app_name)
      response = await self._get_agent_memory_server_client().list_sessions(
          namespace=namespace,
          user_id=user_id,
      )
      sessions = [
          Session(
              id=session_id,
              app_name=app_name,
              user_id=user_id,
              state={},
              events=[],
              last_update_time=time.time(),
          )
          for session_id in getattr(response, "sessions", []) or []
      ]
      return ListSessionsResponse(sessions=sessions)

    except Exception as e:
      logger.error("Failed to list sessions: %s", e)
      return ListSessionsResponse(sessions=[])

  async def _delete_session_agent_memory_server(
      self, *, app_name: str, user_id: str, session_id: str
  ) -> None:
    """Delete a session from the self-hosted Agent Memory Server."""
    try:
      await self._get_agent_memory_server_client().delete_working_memory(
          session_id=session_id,
          namespace=self._get_namespace(app_name),
          user_id=user_id,
      )
      logger.info("Deleted session %s", session_id)
    except Exception as e:
      logger.error("Failed to delete session %s: %s", session_id, e)

  async def _append_event_to_agent_memory_server(
      self, session: Session, event: Event
  ) -> None:
    """Append one ADK event to the self-hosted Agent Memory Server."""
    message = self._event_to_agent_memory_server_message(event)
    if not message:
      return

    await self._get_agent_memory_server_client().append_messages_to_working_memory(
        session_id=session.id,
        messages=[message],
        namespace=self._get_namespace(session.app_name),
        user_id=session.user_id,
    )

  async def _append_event_to_redis(
      self, session: Session, event: Event
  ) -> None:
    """Append one ADK event to Redis Agent Memory."""
    text = extract_text_from_event(event).strip()
    if not text:
      return

    storage_session_id = self._storage_session_id(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    async with self._agent_memory() as agent_memory:
      await agent_memory.add_session_event_async(
          session_id=storage_session_id,
          actor_id=self._event_actor_id(session, event),
          role=self._event_role(event),
          content=[{"text": text}],
          created_at=timestamp_to_datetime(event.timestamp),
          metadata=self._event_metadata(
              event=event,
              app_name=session.app_name,
              user_id=session.user_id,
              session_id=session.id,
          ),
      )

  def _event_text(self, event: object) -> str:
    """Extract text from a Redis Agent Memory session event."""
    content = read_field(event, "content", [])
    parts = []
    for item in content or []:
      text = read_field(item, "text", "")
      if text:
        parts.append(str(text))
    return "\n".join(parts)

  def _response_to_session(
      self,
      response: object,
      *,
      app_name: str,
      user_id: str,
      session_id: str,
  ) -> Session:
    """Convert a Redis Agent Memory session response to an ADK Session."""
    events = []
    state: dict[str, Any] = {}
    response_events = read_field(response, "events", []) or []

    for redis_event in response_events:
      text = self._event_text(redis_event).strip()
      if not text:
        continue

      role_raw = read_field(redis_event, "role", "")
      role = str(getattr(role_raw, "value", role_raw)).lower()
      author = "user" if role == "user" else app_name
      content_role = "user" if role == "user" else "model"
      content = types.Content(
          role=content_role,
          parts=[types.Part(text=text)],
      )
      created_at = read_field(redis_event, "created_at")
      timestamp = created_at.timestamp() if created_at else time.time()
      metadata = read_field(redis_event, "metadata", {}) or {}
      state_delta = metadata.get("state_delta")
      if isinstance(state_delta, dict):
        state.update(state_delta)

      events.append(
          Event(
              id=metadata.get("adk_event_id")
              or read_field(redis_event, "event_id"),
              author=metadata.get("adk_author") or author,
              content=content,
              timestamp=timestamp,
          )
      )

    return Session(
        id=session_id,
        app_name=app_name,
        user_id=user_id,
        events=events,
        state=state,
        last_update_time=time.time(),
    )

  @override
  async def create_session(
      self,
      *,
      app_name: str,
      user_id: str,
      state: dict[str, Any] | None = None,
      session_id: str | None = None,
  ) -> Session:
    """Create a new ADK session object.

    Redis Agent Memory creates a stored session when the first event is
    appended, so this method returns the ADK session without writing a marker
    event.
    """
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      return await self._create_session_agent_memory_server(
          app_name=app_name,
          user_id=user_id,
          state=state,
          session_id=session_id,
      )

    session_id = (
        session_id.strip()
        if session_id and session_id.strip()
        else str(uuid.uuid4())
    )
    return Session(
        id=session_id,
        app_name=app_name,
        user_id=user_id,
        state=state or {},
        events=[],
        last_update_time=time.time(),
    )

  @override
  async def get_session(
      self,
      *,
      app_name: str,
      user_id: str,
      session_id: str,
      config: GetSessionConfig | None = None,
  ) -> Session | None:
    """Retrieve an ADK session from Redis Agent Memory."""
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      return await self._get_session_agent_memory_server(
          app_name=app_name,
          user_id=user_id,
          session_id=session_id,
          config=config,
      )

    storage_session_id = self._storage_session_id(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    try:
      async with self._agent_memory() as agent_memory:
        response = await agent_memory.get_session_memory_async(
            session_id=storage_session_id
        )
    except Exception as e:
      if is_not_found_error(e):
        # Managed sessions are materialized on first append_event. Return an
        # empty ADK session so runners can start a new conversation.
        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state={},
            events=[],
            last_update_time=time.time(),
        )
      logger.error("Failed to get session %s: %s", session_id, e)
      return None

    session = self._response_to_session(
        response,
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )

    if config:
      if config.num_recent_events is not None:
        session.events = session.events[-config.num_recent_events :]
      if config.after_timestamp is not None:
        session.events = [
            event
            for event in session.events
            if event.timestamp >= config.after_timestamp
        ]

    return session

  @override
  async def list_sessions(
      self, *, app_name: str, user_id: str | None = None
  ) -> ListSessionsResponse:
    """List stored sessions from Redis Agent Memory."""
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      return await self._list_sessions_agent_memory_server(
          app_name=app_name,
          user_id=user_id,
      )

    namespace = self._get_namespace(app_name)
    sessions = []
    page_token = None

    try:
      async with self._agent_memory() as agent_memory:
        while True:
          response = await agent_memory.list_sessions_async(
              limit=100,
              page_token=page_token,
          )
          for storage_session_id in read_field(response, "items", []) or []:
            parsed = self._parse_storage_session_id(storage_session_id)
            if parsed:
              stored_namespace, stored_user_id, session_id = parsed
            else:
              try:
                stored = await agent_memory.get_session_memory_async(
                    session_id=storage_session_id
                )
              except Exception:
                continue
              scope = self._session_scope_from_response(stored)
              if not scope:
                continue
              stored_namespace, stored_user_id, session_id = scope
            if stored_namespace != namespace:
              continue
            if user_id is not None and stored_user_id != user_id:
              continue
            sessions.append(
                Session(
                    id=session_id,
                    app_name=app_name,
                    user_id=stored_user_id,
                    state={},
                    events=[],
                    last_update_time=time.time(),
                )
            )

          page_token = read_field(response, "next_page_token")
          if not page_token:
            break

      return ListSessionsResponse(sessions=sessions)

    except Exception as e:
      logger.error("Failed to list sessions: %s", e)
      return ListSessionsResponse(sessions=[])

  @override
  async def delete_session(
      self, *, app_name: str, user_id: str, session_id: str
  ) -> None:
    """Delete a session from Redis Agent Memory."""
    if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
      await self._delete_session_agent_memory_server(
          app_name=app_name,
          user_id=user_id,
          session_id=session_id,
      )
      return

    storage_session_id = self._storage_session_id(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
    )
    try:
      async with self._agent_memory() as agent_memory:
        await agent_memory.delete_session_memory_async(
            session_id=storage_session_id
        )
      logger.info("Deleted session %s", session_id)
    except Exception as e:
      if not is_not_found_error(e):
        logger.error("Failed to delete session %s: %s", session_id, e)

  @override
  async def append_event(self, session: Session, event: Event) -> Event:
    """Append an event to the ADK session and configured backend."""
    appended_event = await super().append_event(session=session, event=event)
    if appended_event.partial:
      return appended_event

    session.last_update_time = appended_event.timestamp
    try:
      if self._config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
        await self._append_event_to_agent_memory_server(
            session,
            appended_event,
        )
      else:
        await self._append_event_to_redis(session, appended_event)
      logger.debug("Appended message to session %s", session.id)
    except Exception as e:
      logger.error("Failed to append event to session %s: %s", session.id, e)

    return appended_event

  async def close(self) -> None:
    """Close the session service and cleanup resources."""
    pass
