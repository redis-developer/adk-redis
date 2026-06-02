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

"""End-to-end integration tests for the selectable memory backends.

Round-trips RedisLongTermMemoryService and RedisWorkingMemorySessionService
against real backends. Tests skip when env vars are not set:

- redis-agent-memory (managed): REDIS_AGENT_MEMORY_API_BASE_URL,
  REDIS_AGENT_MEMORY_API_KEY, REDIS_AGENT_MEMORY_STORE_ID
- opensource-agent-memory (self-hosted): AGENT_MEMORY_SERVER_URL
"""

from __future__ import annotations

import uuid

from google.adk.events.event import Event
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types
import pytest

from adk_redis import RedisLongTermMemoryService
from adk_redis import RedisLongTermMemoryServiceConfig
from adk_redis import RedisWorkingMemorySessionService
from adk_redis import RedisWorkingMemorySessionServiceConfig
from tests.integration.conftest import AGENT_MEMORY_SERVER_URL
from tests.integration.conftest import REDIS_AGENT_MEMORY_API_KEY
from tests.integration.conftest import REDIS_AGENT_MEMORY_STORE_ID
from tests.integration.conftest import REDIS_AGENT_MEMORY_URL
from tests.integration.conftest import REQUIRES_AGENT_MEMORY_SERVER
from tests.integration.conftest import REQUIRES_REDIS_AGENT_MEMORY

pytest.importorskip("agent_memory_client")
pytest.importorskip("redis_agent_memory")

_APP_NAME = "adk_redis_it"
_QUERY = "what color does the user like?"
_MEMORY_TEXT = "The user prefers the color teal."


def _text_event(author: str, text: str) -> Event:
  return Event(
      author=author,
      content=types.Content(role=author, parts=[types.Part(text=text)]),
  )


def _memory_entry(text: str) -> MemoryEntry:
  return MemoryEntry(
      content=types.Content(parts=[types.Part(text=text)]),
      custom_metadata={"memory_type": "semantic"},
  )


def _text_of(parts_owner) -> str:
  if parts_owner and parts_owner.content and parts_owner.content.parts:
    return (parts_owner.content.parts[0].text or "").lower()
  return ""


@REQUIRES_REDIS_AGENT_MEMORY
class TestRedisAgentMemoryBackendEndToEnd:
  """Round-trip the managed Redis Agent Memory backend."""

  def _long_term(self, namespace: str) -> RedisLongTermMemoryService:
    return RedisLongTermMemoryService(
        config=RedisLongTermMemoryServiceConfig(
            backend="redis-agent-memory",
            api_base_url=REDIS_AGENT_MEMORY_URL,
            api_key=REDIS_AGENT_MEMORY_API_KEY,
            store_id=REDIS_AGENT_MEMORY_STORE_ID,
            default_namespace=namespace,
            search_top_k=5,
        )
    )

  async def test_add_memory_then_search(
      self, unique_namespace: str, unique_user_id: str
  ) -> None:
    service = self._long_term(unique_namespace)
    await service.add_memory(
        app_name=_APP_NAME,
        user_id=unique_user_id,
        memories=[_memory_entry(_MEMORY_TEXT)],
    )
    response = await service.search_memory(
        app_name=_APP_NAME, user_id=unique_user_id, query=_QUERY
    )
    assert any("teal" in _text_of(m) for m in response.memories)

  async def test_session_append_and_get(
      self, unique_namespace: str, unique_user_id: str
  ) -> None:
    sessions = RedisWorkingMemorySessionService(
        config=RedisWorkingMemorySessionServiceConfig(
            backend="redis-agent-memory",
            api_base_url=REDIS_AGENT_MEMORY_URL,
            api_key=REDIS_AGENT_MEMORY_API_KEY,
            store_id=REDIS_AGENT_MEMORY_STORE_ID,
            default_namespace=unique_namespace,
        )
    )
    session_id = f"sess_{uuid.uuid4().hex[:8]}"
    session = await sessions.create_session(
        app_name=_APP_NAME, user_id=unique_user_id, session_id=session_id
    )
    await sessions.append_event(
        session=session, event=_text_event("user", "hi from integration test")
    )
    fetched = await sessions.get_session(
        app_name=_APP_NAME, user_id=unique_user_id, session_id=session_id
    )
    assert fetched is not None and fetched.id == session_id
    assert any("integration test" in _text_of(e) for e in fetched.events)
    await sessions.delete_session(
        app_name=_APP_NAME, user_id=unique_user_id, session_id=session_id
    )


@REQUIRES_AGENT_MEMORY_SERVER
class TestAgentMemoryServerBackendEndToEnd:
  """Round-trip the self-hosted Agent Memory Server backend."""

  async def test_add_memory_then_search(
      self, unique_namespace: str, unique_user_id: str
  ) -> None:
    service = RedisLongTermMemoryService(
        config=RedisLongTermMemoryServiceConfig(
            backend="opensource-agent-memory",
            api_base_url=AGENT_MEMORY_SERVER_URL,
            default_namespace=unique_namespace,
            search_top_k=5,
            recency_boost=False,
        )
    )
    try:
      await service.add_memory(
          app_name=_APP_NAME,
          user_id=unique_user_id,
          memories=[_memory_entry(_MEMORY_TEXT)],
      )
      response = await service.search_memory(
          app_name=_APP_NAME, user_id=unique_user_id, query=_QUERY
      )
      assert isinstance(response.memories, list)
    finally:
      await service.close()
