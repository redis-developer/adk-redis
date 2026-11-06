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

"""Check the requests adk-redis builds against the installed SDK's models.

The SDK validates request dictionaries against its pydantic models and drops
keys it does not recognise, so a renamed field fails silently: a search loses
its query and namespace filter and still succeeds. These tests capture what
adk-redis sends through a recording client and require every key to survive
validation by the real Redis Agent Memory models.
"""

import inspect
from types import SimpleNamespace
from unittest.mock import patch

from google.adk.events.event import Event
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session
from google.genai import types
import pytest

from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig
from adk_redis.sessions import RedisSessionMemoryService
from adk_redis.sessions import RedisSessionMemoryServiceConfig
from adk_redis.tools.memory import CreateMemoryTool
from adk_redis.tools.memory import MemoryToolConfig
from adk_redis.tools.memory import SearchMemoryTool
from adk_redis.tools.memory import UpdateMemoryTool
from tests.agent_memory_fakes import FakeNamespaces
from tests.agent_memory_fakes import namespace_id_for

models = pytest.importorskip("redis_agent_memory.models")
AgentMemory = pytest.importorskip("redis_agent_memory").AgentMemory


def _assert_survives(model, payload):
  """Require every key in payload to round-trip through an SDK model."""
  validated = model.model_validate(payload)
  dumped = validated.model_dump(by_alias=True, exclude_none=True, mode="json")
  expected = {key: value for key, value in payload.items() if value is not None}
  assert dumped == expected


def _assert_binds(method_name, kwargs):
  """Require keyword arguments to match an SDK method's signature."""
  inspect.signature(getattr(AgentMemory, method_name)).bind(None, **kwargs)


class RecordingAgentMemory(FakeNamespaces):
  """Fake client that records every request adk-redis sends."""

  def __init__(self):
    self.init_namespaces("app")
    self.calls = {}

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    return None

  async def bulk_create_long_term_memories_async(self, **kwargs):
    self.calls["bulk_create_long_term_memories_async"] = kwargs
    return SimpleNamespace(created=[], errors=None)

  async def search_long_term_memory_async(self, **kwargs):
    self.calls["search_long_term_memory_async"] = kwargs
    return SimpleNamespace(items=[])

  async def get_long_term_memory_async(self, **kwargs):
    return SimpleNamespace(
        memory_id=kwargs["memory_id"],
        namespace_id=namespace_id_for("app"),
        owner_id="alice",
        revision="rev-1",
    )

  async def update_long_term_memory_async(self, **kwargs):
    self.calls["update_long_term_memory_async"] = kwargs
    return SimpleNamespace(memory_id=kwargs["memory_id"])

  async def add_session_event_async(self, **kwargs):
    self.calls["add_session_event_async"] = kwargs

  async def list_sessions_async(self, **kwargs):
    self.calls["list_sessions_async"] = kwargs
    return SimpleNamespace(items=[], next_cursor=None)


@pytest.fixture
def client():
  return RecordingAgentMemory()


@pytest.mark.asyncio
async def test_service_search_request_matches_sdk_model(client):
  service = RedisLongTermMemoryService(
      RedisLongTermMemoryServiceConfig(similarity_threshold=0.5)
  )
  with patch.object(service, "_get_client", return_value=client):
    await service.search_memory(app_name="app", user_id="alice", query="tea")

  request = client.calls["search_long_term_memory_async"]["request"]
  _assert_survives(models.SearchLongTermMemoryRequestContent, request)
  assert request["query"] == "tea"


@pytest.mark.asyncio
async def test_service_memory_records_match_sdk_model(client):
  service = RedisLongTermMemoryService()
  memory = MemoryEntry(
      content=types.Content(parts=[types.Part(text="User likes tea.")])
  )
  with patch.object(service, "_get_client", return_value=client):
    await service.add_memory(app_name="app", user_id="alice", memories=[memory])

  call = client.calls["bulk_create_long_term_memories_async"]
  _assert_binds("bulk_create_long_term_memories_async", call)
  for record in call["memories"]:
    _assert_survives(models.CreateMemoryRecord, record)


@pytest.mark.asyncio
async def test_tool_search_and_create_match_sdk_models(client):
  config = MemoryToolConfig(default_namespace="app", default_owner_id="alice")

  search = SearchMemoryTool(config=config)
  with patch.object(search, "_get_client", return_value=client):
    await search.run_async(args={"query": "tea"})
  _assert_survives(
      models.SearchLongTermMemoryRequestContent,
      client.calls["search_long_term_memory_async"]["request"],
  )

  create = CreateMemoryTool(config=config)
  with patch.object(create, "_get_client", return_value=client):
    await create.run_async(args={"content": "User likes tea."})
  for record in client.calls["bulk_create_long_term_memories_async"][
      "memories"
  ]:
    _assert_survives(models.CreateMemoryRecord, record)


@pytest.mark.asyncio
async def test_tool_update_matches_sdk_signature(client):
  config = MemoryToolConfig(default_namespace="app", default_owner_id="alice")
  tool = UpdateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=client):
    await tool.run_async(args={"memory_id": "memory-1", "content": "Updated"})

  _assert_binds(
      "update_long_term_memory_async",
      client.calls["update_long_term_memory_async"],
  )


@pytest.mark.asyncio
async def test_session_calls_match_sdk_signatures(client):
  service = RedisSessionMemoryService(RedisSessionMemoryServiceConfig())
  session = Session(id="s1", app_name="app", user_id="alice")
  event = Event(
      author="user",
      content=types.Content(role="user", parts=[types.Part(text="Hello")]),
  )
  with patch.object(service, "_get_client", return_value=client):
    await service.append_event(session, event)
    await service.list_sessions(app_name="app", user_id="alice")

  _assert_binds(
      "add_session_event_async", client.calls["add_session_event_async"]
  )
  _assert_binds("list_sessions_async", client.calls["list_sessions_async"])


def test_namespace_calls_match_sdk_signatures():
  _assert_binds(
      "list_namespaces_async", {"scope": "SHARED", "limit": 200, "cursor": None}
  )
  _assert_binds(
      "create_namespace_async",
      {"request": {"name": "app", "scope": "SHARED"}},
  )
  _assert_survives(
      models.CreateNamespaceRequestContent, {"name": "app", "scope": "SHARED"}
  )
