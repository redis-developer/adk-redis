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

"""Live checks of namespace placement and isolation on Redis Agent Memory 1.0.

The services log and swallow backend errors, so a round trip can pass while
records land in the wrong place. These tests read the store back through the
SDK to check where adk-redis put each record. They skip unless
REDIS_AGENT_MEMORY_API_BASE_URL, REDIS_AGENT_MEMORY_API_KEY and
REDIS_AGENT_MEMORY_STORE_ID are set.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import uuid

from google.adk.events.event import Event
from google.adk.memory.memory_entry import MemoryEntry
from google.genai import types
import pytest

from adk_redis import REDIS_AGENT_MEMORY_BACKEND
from adk_redis import RedisLongTermMemoryService
from adk_redis import RedisLongTermMemoryServiceConfig
from adk_redis import RedisSessionMemoryService
from adk_redis import RedisSessionMemoryServiceConfig
from adk_redis.memory._namespaces import resolve_namespace_id
from adk_redis.tools.memory import CreateMemoryTool
from adk_redis.tools.memory import DeleteMemoryTool
from adk_redis.tools.memory import MemoryToolConfig
from adk_redis.tools.memory import SearchMemoryTool
from adk_redis.tools.memory import UpdateMemoryTool
from tests.integration.conftest import REDIS_AGENT_MEMORY_API_KEY
from tests.integration.conftest import REDIS_AGENT_MEMORY_STORE_ID
from tests.integration.conftest import REDIS_AGENT_MEMORY_URL
from tests.integration.conftest import REQUIRES_REDIS_AGENT_MEMORY

redis_agent_memory = pytest.importorskip("redis_agent_memory")

pytestmark = REQUIRES_REDIS_AGENT_MEMORY

_APP_NAME = "adk_redis_it"
_CONNECTION = {
    "backend": REDIS_AGENT_MEMORY_BACKEND,
    "api_base_url": REDIS_AGENT_MEMORY_URL,
    "api_key": REDIS_AGENT_MEMORY_API_KEY,
    "store_id": REDIS_AGENT_MEMORY_STORE_ID,
}


def _client():
  return redis_agent_memory.AgentMemory(
      REDIS_AGENT_MEMORY_URL,
      api_key=REDIS_AGENT_MEMORY_API_KEY,
      store_id=REDIS_AGENT_MEMORY_STORE_ID,
  )


async def _lookup(name: str) -> str | None:
  async with _client() as client:
    return await resolve_namespace_id(
        client,
        server_url=REDIS_AGENT_MEMORY_URL or "",
        store_id=REDIS_AGENT_MEMORY_STORE_ID,
        name=name,
        create=False,
    )


async def _eventually(check, attempts: int = 10):
  """Retry a read until it holds, for search indexing that lags writes."""
  for _ in range(attempts - 1):
    result = await check()
    if result:
      return result
    await asyncio.sleep(1)
  return await check()


async def test_memory_lands_in_a_shared_root_named_after_the_namespace(
    unique_namespace: str, unique_user_id: str
) -> None:
  service = RedisLongTermMemoryService(
      RedisLongTermMemoryServiceConfig(
          **_CONNECTION, default_namespace=unique_namespace
      )
  )
  memory_id = f"adk-{uuid.uuid4().hex}"
  await service.add_memory(
      app_name=_APP_NAME,
      user_id=unique_user_id,
      memories=[
          MemoryEntry(
              id=memory_id,
              content=types.Content(parts=[types.Part(text="Likes teal.")]),
          )
      ],
  )

  sanitized = unique_namespace.replace("_", "-")
  async with _client() as client:
    namespace = None
    cursor = None
    while namespace is None:
      page = await client.list_namespaces_async(
          scope="SHARED", limit=200, cursor=cursor
      )
      namespace = next((n for n in page.items if n.name == sanitized), None)
      cursor = page.next_cursor
      if not cursor:
        break
    assert namespace is not None
    assert namespace.parent_id is None
    record = await client.get_long_term_memory_async(memory_id=memory_id)

  assert record.namespace_id == namespace.namespace_id
  assert record.owner_id == unique_user_id


async def test_search_in_another_namespace_finds_nothing_and_creates_nothing(
    unique_namespace: str, unique_user_id: str
) -> None:
  writer = RedisLongTermMemoryService(
      RedisLongTermMemoryServiceConfig(
          **_CONNECTION, default_namespace=unique_namespace
      )
  )
  await writer.add_memory(
      app_name=_APP_NAME,
      user_id=unique_user_id,
      memories=[
          MemoryEntry(
              content=types.Content(parts=[types.Part(text="Likes teal.")])
          )
      ],
  )

  async def found_by_writer():
    response = await writer.search_memory(
        app_name=_APP_NAME, user_id=unique_user_id, query="favourite colour"
    )
    return response.memories

  assert await _eventually(found_by_writer)

  other_namespace = f"{unique_namespace}-other"
  reader = RedisLongTermMemoryService(
      RedisLongTermMemoryServiceConfig(
          **_CONNECTION, default_namespace=other_namespace
      )
  )
  response = await reader.search_memory(
      app_name=_APP_NAME, user_id=unique_user_id, query="favourite colour"
  )

  assert response.memories == []
  assert await _lookup(other_namespace.replace("_", "-")) is None


async def test_list_sessions_returns_sessions_in_the_namespace(
    unique_namespace: str, unique_user_id: str
) -> None:
  sessions = RedisSessionMemoryService(
      RedisSessionMemoryServiceConfig(
          **_CONNECTION, default_namespace=unique_namespace
      )
  )
  session_id = f"sess_{uuid.uuid4().hex[:8]}"
  session = await sessions.create_session(
      app_name=_APP_NAME, user_id=unique_user_id, session_id=session_id
  )
  await sessions.append_event(
      session=session,
      event=Event(
          author="user",
          content=types.Content(role="user", parts=[types.Part(text="Hello")]),
      ),
  )

  async def listed():
    response = await sessions.list_sessions(
        app_name=_APP_NAME, user_id=unique_user_id
    )
    return [s.id for s in response.sessions]

  try:
    assert await _eventually(listed) == [session_id]
  finally:
    await sessions.delete_session(
        app_name=_APP_NAME, user_id=unique_user_id, session_id=session_id
    )


async def test_tools_create_search_update_and_delete_within_scope(
    unique_namespace: str, unique_user_id: str
) -> None:
  config = MemoryToolConfig(
      **_CONNECTION,
      default_namespace=unique_namespace,
      default_owner_id=unique_user_id,
  )
  context = SimpleNamespace(user_id=unique_user_id)

  created = await CreateMemoryTool(config=config).run_async(
      args={"content": "The user's seat preference is the window."},
      tool_context=context,
  )
  assert created["status"] == "success", created
  memory_id = created["memory_id"]

  async def found():
    result = await SearchMemoryTool(config=config).run_async(
        args={"query": "seat preference"}, tool_context=context
    )
    return [m["id"] for m in result.get("memories", [])]

  assert memory_id in await _eventually(found)

  updated = await UpdateMemoryTool(config=config).run_async(
      args={"memory_id": memory_id, "content": "The user prefers aisle seats."},
      tool_context=context,
  )
  assert updated["status"] == "success", updated

  intruder = await DeleteMemoryTool(config=config).run_async(
      args={"memory_ids": [memory_id]},
      tool_context=SimpleNamespace(user_id=f"{unique_user_id}-intruder"),
  )
  assert intruder["status"] == "error"

  deleted = await DeleteMemoryTool(config=config).run_async(
      args={"memory_ids": [memory_id]}, tool_context=context
  )
  assert deleted == {
      "status": "success",
      "deleted_count": 1,
      "message": "Deleted memories",
  }
