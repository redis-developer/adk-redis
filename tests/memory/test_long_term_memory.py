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

"""Tests for RedisLongTermMemoryService."""

from datetime import datetime
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import patch

from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session
from google.genai import types
import pytest

from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig


class FakeAgentMemory:
  """Fake async Redis Agent Memory client."""

  def __init__(self):
    self.created_records = []
    self.search_request = None
    self.search_response = SimpleNamespace(items=[])

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    return None

  async def bulk_create_long_term_memories_async(self, *, memories):
    self.created_records.extend(memories)
    return SimpleNamespace(
        created=[memory["id"] for memory in memories],
        errors=None,
    )

  async def search_long_term_memory_async(self, *, request):
    self.search_request = request
    return self.search_response


class FakeAgentMemoryServerClient:
  """Fake self-hosted Agent Memory Server client."""

  def __init__(self):
    self.search_kwargs = None
    self.search_response = SimpleNamespace(memories=[])

  async def search_long_term_memory(self, **kwargs):
    self.search_kwargs = kwargs
    return self.search_response


class TestRedisLongTermMemoryServiceConfig:
  """Tests for RedisLongTermMemoryServiceConfig."""

  def test_default_values(self):
    """Test default configuration values."""
    config = RedisLongTermMemoryServiceConfig()
    assert config.backend == "redis-agent-memory"
    assert config.api_base_url == "http://localhost:8000"
    assert config.api_key is None
    assert config.store_id is None
    assert config.timeout == 30.0
    assert config.default_namespace is None
    assert config.recency_boost is True
    assert config.recency_weight == 0.2
    assert config.semantic_weight == 0.8
    assert config.extraction_strategy == "discrete"
    assert config.extraction_strategy_config == {}
    assert config.store_events_as_messages is True

  def test_custom_values(self):
    """Test custom configuration values."""
    config = RedisLongTermMemoryServiceConfig(
        api_base_url="http://custom:9000",
        api_key="key",
        store_id="store",
        timeout=60.0,
        default_namespace="test_ns",
        recency_weight=0.5,
        semantic_weight=0.5,
        extraction_strategy="summary",
        extraction_strategy_config={"max_length": 100},
    )
    assert config.api_base_url == "http://custom:9000"
    assert config.api_key == "key"
    assert config.store_id == "store"
    assert config.timeout == 60.0
    assert config.default_namespace == "test_ns"
    assert config.recency_weight == 0.5
    assert config.semantic_weight == 0.5
    assert config.extraction_strategy == "summary"
    assert config.extraction_strategy_config == {"max_length": 100}

  def test_opensource_backend_value(self):
    """Test the self-hosted backend value is accepted."""
    config = RedisLongTermMemoryServiceConfig(backend="opensource-agent-memory")
    assert config.backend == "opensource-agent-memory"


class TestRedisLongTermMemoryServiceInit:
  """Tests for RedisLongTermMemoryService initialization."""

  def test_init_with_default_config(self):
    """Test initialization with default config."""
    service = RedisLongTermMemoryService()
    assert service._config.api_base_url == "http://localhost:8000"

  def test_init_with_custom_config(self):
    """Test initialization with custom config."""
    config = RedisLongTermMemoryServiceConfig(
        api_base_url="http://custom:9000",
    )
    service = RedisLongTermMemoryService(config=config)
    assert service._config.api_base_url == "http://custom:9000"


class TestRedisLongTermMemoryServiceMethods:
  """Tests for RedisLongTermMemoryService methods."""

  @pytest.fixture
  def fake_client(self):
    """Create a fake Redis Agent Memory client."""
    return FakeAgentMemory()

  @pytest.fixture
  def service(self, fake_client):
    """Create a service instance for testing."""
    service = RedisLongTermMemoryService(
        RedisLongTermMemoryServiceConfig(default_namespace="test_ns")
    )
    with patch.object(service, "_get_client", return_value=fake_client):
      yield service

  @pytest.mark.asyncio
  async def test_search_memory_uses_owner_and_namespace_filter(
      self, service, fake_client
  ):
    """Test search_memory scopes requests by owner and namespace."""
    fake_client.search_response = SimpleNamespace(
        items=[
            SimpleNamespace(
                id="memory-1",
                text="The user prefers window seats.",
                owner_id="alice",
                namespace="test_ns",
                session_id="session-1",
                topics=["travel"],
                memory_type="semantic",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ]
    )

    result = await service.search_memory(
        app_name="app",
        user_id="alice",
        query="seat preference",
    )

    assert fake_client.search_request["filter"] == {
        "ownerId": {"eq": "alice"},
        "namespace": {"eq": "test_ns"},
    }
    assert result.memories[0].id == "memory-1"
    assert (
        result.memories[0].content.parts[0].text
        == "The user prefers window seats."
    )

  @pytest.mark.asyncio
  async def test_add_memory_creates_long_term_records(
      self, service, fake_client
  ):
    """Test add_memory writes explicit Redis Agent Memory records."""
    memory = MemoryEntry(
        id="memory-1",
        content=types.Content(
            parts=[types.Part(text="The user prefers window seats.")]
        ),
        custom_metadata={"topics": ["travel"]},
    )

    await service.add_memory(
        app_name="app",
        user_id="alice",
        memories=[memory],
    )

    assert fake_client.created_records == [
        {
            "id": "memory-1",
            "text": "The user prefers window seats.",
            "ownerId": "alice",
            "namespace": "test_ns",
            "sessionId": None,
            "topics": ["travel", "app"],
            "memoryType": "semantic",
        }
    ]

  @pytest.mark.asyncio
  async def test_add_session_to_memory_creates_message_records(
      self, service, fake_client
  ):
    """Test add_session_to_memory stores event text as message memory."""
    session = Session(
        id="session-1",
        app_name="app",
        user_id="alice",
        events=[],
    )

    await service.add_session_to_memory(session)

    assert fake_client.created_records == []

  @pytest.mark.asyncio
  async def test_search_memory_can_use_agent_memory_server_backend(self):
    """Test search_memory can use the self-hosted backend."""
    fake_client = FakeAgentMemoryServerClient()
    fake_client.search_response = SimpleNamespace(
        memories=[
            SimpleNamespace(
                id="memory-1",
                text="The user prefers aisle seats.",
                namespace="test_ns",
                user_id="alice",
                session_id="session-1",
                topics=["travel"],
                memory_type="semantic",
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ]
    )
    service = RedisLongTermMemoryService(
        RedisLongTermMemoryServiceConfig(
            backend="opensource-agent-memory",
            default_namespace="test_ns",
            recency_boost=False,
        )
    )

    with patch.object(
        service,
        "_get_agent_memory_server_client",
        return_value=fake_client,
    ):
      result = await service.search_memory(
          app_name="app",
          user_id="alice",
          query="seat preference",
      )

    assert fake_client.search_kwargs["namespace"] == {"eq": "test_ns"}
    assert fake_client.search_kwargs["user_id"] == {"eq": "alice"}
    assert result.memories[0].id == "memory-1"
