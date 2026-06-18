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

"""Tests for RedisWorkingMemorySessionService."""

from datetime import datetime
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import patch

from google.adk.events.event import Event
from google.adk.sessions.session import Session
from google.genai import types
import pytest

from adk_redis import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis import REDIS_AGENT_MEMORY_BACKEND
from adk_redis.sessions import RedisWorkingMemorySessionService
from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig


class FakeAgentMemory:
  """Fake async Redis Agent Memory client."""

  def __init__(self):
    self.added_events = []
    self.deleted_session_id = None
    self.get_response = None
    self.list_response = SimpleNamespace(items=[], next_page_token=None)

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    return None

  async def add_session_event_async(self, **kwargs):
    self.added_events.append(kwargs)
    return SimpleNamespace(event=kwargs)

  async def get_session_memory_async(self, *, session_id):
    if self.get_response is None:
      error = RuntimeError("not found")
      error.status_code = 404  # type: ignore[attr-defined]
      raise error
    return self.get_response

  async def delete_session_memory_async(self, *, session_id):
    self.deleted_session_id = session_id

  async def list_sessions_async(self, *, limit, page_token):
    return self.list_response


class FakeAgentMemoryServerClient:
  """Fake self-hosted Agent Memory Server client."""

  def __init__(self):
    self.list_kwargs = None
    self.list_response = SimpleNamespace(sessions=[])

  async def list_sessions(self, **kwargs):
    self.list_kwargs = kwargs
    return self.list_response


class TestRedisWorkingMemorySessionServiceConfig:
  """Tests for RedisWorkingMemorySessionServiceConfig."""

  def test_default_values(self):
    """Test default configuration values."""
    config = RedisWorkingMemorySessionServiceConfig()
    assert config.backend == REDIS_AGENT_MEMORY_BACKEND
    assert config.api_base_url == "http://localhost:8000"
    assert config.api_key is None
    assert config.store_id is None
    assert config.timeout == 30.0
    assert config.default_namespace is None
    assert config.model_name is None
    assert config.context_window_max is None
    assert config.extraction_strategy == "discrete"
    assert config.extraction_strategy_config == {}
    assert config.session_ttl_seconds is None

  def test_custom_values(self):
    """Test custom configuration values."""
    config = RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://custom:9000",
        api_key="key",
        store_id="store",
        timeout=60.0,
        default_namespace="test_ns",
        model_name="gpt-4",
        context_window_max=8000,
        extraction_strategy="summary",
        session_ttl_seconds=3600,
    )
    assert config.api_base_url == "http://custom:9000"
    assert config.api_key == "key"
    assert config.store_id == "store"
    assert config.timeout == 60.0
    assert config.default_namespace == "test_ns"
    assert config.model_name == "gpt-4"
    assert config.context_window_max == 8000
    assert config.extraction_strategy == "summary"
    assert config.session_ttl_seconds == 3600

  def test_opensource_backend_value(self):
    """Test the self-hosted backend value is accepted."""
    config = RedisWorkingMemorySessionServiceConfig(
        backend=OPENSOURCE_AGENT_MEMORY_BACKEND
    )
    assert config.backend == OPENSOURCE_AGENT_MEMORY_BACKEND


class TestRedisWorkingMemorySessionServiceInit:
  """Tests for RedisWorkingMemorySessionService initialization."""

  def test_init_with_default_config(self):
    """Test initialization with default config."""
    service = RedisWorkingMemorySessionService()
    assert service._config.api_base_url == "http://localhost:8000"

  def test_init_with_custom_config(self):
    """Test initialization with custom config."""
    config = RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://custom:9000",
    )
    service = RedisWorkingMemorySessionService(config=config)
    assert service._config.api_base_url == "http://custom:9000"


class TestRedisWorkingMemorySessionServiceMethods:
  """Tests for RedisWorkingMemorySessionService methods."""

  @pytest.fixture
  def fake_client(self):
    """Create a fake Redis Agent Memory client."""
    return FakeAgentMemory()

  @pytest.fixture
  def service(self, fake_client):
    """Create a service instance for testing."""
    service = RedisWorkingMemorySessionService(
        RedisWorkingMemorySessionServiceConfig(default_namespace="test_ns")
    )
    with patch.object(service, "_get_client", return_value=fake_client):
      yield service

  def test_storage_session_id_uses_managed_safe_hex(self, service):
    """Test managed storage session IDs fit API charset and length limits."""
    storage_id = service._storage_session_id(
        app_name="app",
        user_id="alice",
        session_id="session-1",
    )

    assert len(storage_id) == 64
    assert storage_id.isalnum()
    assert (
        service._storage_session_id(
            app_name="app",
            user_id="alice",
            session_id="session-1",
        )
        == storage_id
    )

  def test_storage_session_id_hashes_uuid_session_ids(self, service):
    """Test ADK UUID session IDs map to deterministic managed storage IDs."""
    storage_id = service._storage_session_id(
        app_name="app",
        user_id="user",
        session_id="28a7d6e2-0f0f-43b6-b22c-47e03635ed34",
    )

    assert len(storage_id) == 64
    assert storage_id.isalnum()

  @pytest.mark.asyncio
  async def test_append_event_writes_session_event(self, service, fake_client):
    """Test append_event stores a Redis Agent Memory session event."""
    session = Session(
        id="session-1",
        app_name="app",
        user_id="alice",
        events=[],
    )
    event = Event(
        id="event-1",
        author="user",
        content=types.Content(
            role="user",
            parts=[types.Part(text="I prefer window seats.")],
        ),
        timestamp=1700000000,
    )

    await service.append_event(session, event)

    assert len(fake_client.added_events) == 1
    stored = fake_client.added_events[0]
    assert stored["actor_id"] == "alice"
    assert stored["content"] == [{"text": "I prefer window seats."}]
    assert stored["metadata"]["namespace"] == "test-ns"
    assert stored["metadata"]["adk_event_id"] == "event-1"

  @pytest.mark.asyncio
  async def test_get_session_returns_empty_before_first_event(
      self, service, fake_client
  ):
    """Test get_session returns an empty session before Redis materializes it."""
    session = await service.get_session(
        app_name="app",
        user_id="alice",
        session_id="fa58803d-9a11-4466-8f3f-40baf61b41c0",
    )

    assert session is not None
    assert session.id == "fa58803d-9a11-4466-8f3f-40baf61b41c0"
    assert session.events == []

  @pytest.mark.asyncio
  async def test_get_session_reconstructs_adk_events(
      self, service, fake_client
  ):
    """Test get_session converts Redis events into ADK events."""
    storage_id = service._storage_session_id(
        app_name="app",
        user_id="alice",
        session_id="session-1",
    )
    fake_client.get_response = SimpleNamespace(
        session_id=storage_id,
        owner_id="alice",
        events=[
            SimpleNamespace(
                event_id="redis-event-1",
                actor_id="alice",
                role="user",
                content=[{"text": "I prefer window seats."}],
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                metadata={
                    "adk_event_id": "event-1",
                    "adk_author": "user",
                    "state_delta": {"seat": "window"},
                },
            )
        ],
    )

    session = await service.get_session(
        app_name="app",
        user_id="alice",
        session_id="session-1",
    )

    assert session is not None
    assert session.id == "session-1"
    assert session.state == {"seat": "window"}
    assert session.events[0].id == "event-1"
    assert session.events[0].content.parts[0].text == "I prefer window seats."

  @pytest.mark.asyncio
  async def test_list_sessions_resolves_storage_ids_from_metadata(
      self, service, fake_client
  ):
    """Test list_sessions resolves managed storage IDs from event metadata."""
    storage_id = service._storage_session_id(
        app_name="app",
        user_id="alice",
        session_id="28a7d6e2-0f0f-43b6-b22c-47e03635ed34",
    )
    fake_client.get_response = SimpleNamespace(
        session_id=storage_id,
        owner_id="alice",
        events=[
            SimpleNamespace(
                metadata={
                    "namespace": "test-ns",
                    "user_id": "alice",
                    "adk_session_id": "28a7d6e2-0f0f-43b6-b22c-47e03635ed34",
                }
            )
        ],
    )
    fake_client.list_response = SimpleNamespace(
        items=[storage_id],
        next_page_token=None,
    )

    response = await service.list_sessions(app_name="app", user_id="alice")

    assert [session.id for session in response.sessions] == [
        "28a7d6e2-0f0f-43b6-b22c-47e03635ed34"
    ]

  @pytest.mark.asyncio
  async def test_list_sessions_filters_internal_ids(self, service, fake_client):
    """Test list_sessions filters by namespace and user."""
    storage_id = service._storage_session_id(
        app_name="app",
        user_id="alice",
        session_id="session-1",
    )
    fake_client.get_response = SimpleNamespace(
        session_id=storage_id,
        owner_id="alice",
        events=[
            SimpleNamespace(
                metadata={
                    "namespace": "test-ns",
                    "user_id": "alice",
                    "adk_session_id": "session-1",
                }
            )
        ],
    )
    fake_client.list_response = SimpleNamespace(
        items=[storage_id],
        next_page_token=None,
    )

    response = await service.list_sessions(app_name="app", user_id="alice")

    assert [session.id for session in response.sessions] == ["session-1"]
    response_other_user = await service.list_sessions(
        app_name="app", user_id="bob"
    )
    assert response_other_user.sessions == []

  @pytest.mark.asyncio
  async def test_close_completes_without_error(self, service):
    """Test close method completes without error."""
    await service.close()

  @pytest.mark.asyncio
  async def test_list_sessions_can_use_agent_memory_server_backend(self):
    """Test list_sessions can use the self-hosted backend."""
    fake_client = FakeAgentMemoryServerClient()
    fake_client.list_response = SimpleNamespace(sessions=["session-1"])
    service = RedisWorkingMemorySessionService(
        RedisWorkingMemorySessionServiceConfig(
            backend=OPENSOURCE_AGENT_MEMORY_BACKEND,
            default_namespace="test_ns",
        )
    )

    with patch.object(
        service,
        "_get_agent_memory_server_client",
        return_value=fake_client,
    ):
      response = await service.list_sessions(app_name="app", user_id="alice")

    assert fake_client.list_kwargs == {
        "namespace": "test_ns",
        "user_id": "alice",
    }
    assert [session.id for session in response.sessions] == ["session-1"]
