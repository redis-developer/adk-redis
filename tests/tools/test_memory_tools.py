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

"""Tests for Redis Agent Memory tools."""

import asyncio
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from adk_redis import OPENSOURCE_AGENT_MEMORY_BACKEND
from adk_redis import REDIS_AGENT_MEMORY_BACKEND
from adk_redis.memory._utils import stable_memory_id
from adk_redis.tools.memory import CreateMemoryTool
from adk_redis.tools.memory import DeleteMemoryTool
from adk_redis.tools.memory import MemoryPromptTool
from adk_redis.tools.memory import MemoryToolConfig
from adk_redis.tools.memory import SearchMemoryTool
from adk_redis.tools.memory import UpdateMemoryTool


class FakeAgentMemory:
  """Fake async Redis Agent Memory client."""

  def __init__(self):
    self.created_records = []
    self.deleted_ids = []
    self.search_request = None
    self.update_kwargs = None
    self.memory_namespace = "test-ns"
    self.memory_owner_id = "alice"
    self.active_gets = 0
    self.max_concurrent_gets = 0

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
    return SimpleNamespace(
        items=[
            SimpleNamespace(
                id="memory-1",
                text="The user prefers window seats.",
                topics=["travel"],
                memory_type="semantic",
                created_at=None,
            )
        ]
    )

  async def update_long_term_memory_async(self, **kwargs):
    self.update_kwargs = kwargs
    return SimpleNamespace(id=kwargs["memory_id"])

  async def get_long_term_memory_async(self, *, memory_id):
    self.active_gets += 1
    self.max_concurrent_gets = max(self.max_concurrent_gets, self.active_gets)
    try:
      await asyncio.sleep(0)
      return SimpleNamespace(
          id=memory_id,
          namespace=self.memory_namespace,
          owner_id=self.memory_owner_id,
      )
    finally:
      self.active_gets -= 1

  async def bulk_delete_long_term_memories_async(self, *, memory_ids):
    self.deleted_ids.extend(memory_ids)
    return SimpleNamespace(deleted=memory_ids, errors=None)


class FakeAgentMemoryServerClient:
  """Fake self-hosted Agent Memory Server client."""

  def __init__(self):
    self.add_memory_kwargs = None
    self.edit_memory_kwargs = None
    self.deleted_ids = []
    self.memory_namespace = "test_ns"
    self.memory_user_id = "alice"
    self.active_gets = 0
    self.max_concurrent_gets = 0

  async def add_memory_tool(self, **kwargs):
    self.add_memory_kwargs = kwargs
    return {
        "success": True,
        "memory_id": "memory-1",
        "summary": "Memory created successfully",
    }

  async def get_long_term_memory(self, *, memory_id):
    self.active_gets += 1
    self.max_concurrent_gets = max(self.max_concurrent_gets, self.active_gets)
    try:
      await asyncio.sleep(0)
      return SimpleNamespace(
          id=memory_id,
          namespace=self.memory_namespace,
          user_id=self.memory_user_id,
      )
    finally:
      self.active_gets -= 1

  async def edit_long_term_memory(self, **kwargs):
    self.edit_memory_kwargs = kwargs
    return SimpleNamespace(id=kwargs["memory_id"])

  async def delete_long_term_memories(self, *, memory_ids):
    self.deleted_ids.extend(memory_ids)
    return SimpleNamespace(status=f"ok: deleted {len(memory_ids)}")


@pytest.fixture
def config():
  """Create memory tool config."""
  return MemoryToolConfig(
      default_namespace="test_ns",
      default_owner_id="alice",
  )


@pytest.fixture
def fake_client():
  """Create fake Redis Agent Memory client."""
  return FakeAgentMemory()


def test_memory_tool_config_accepts_opensource_backend():
  """Memory tool config accepts the self-hosted backend value."""
  assert (
      MemoryToolConfig(backend=OPENSOURCE_AGENT_MEMORY_BACKEND).backend
      == OPENSOURCE_AGENT_MEMORY_BACKEND
  )


def test_get_user_id_resolution_order(config):
  """_get_user_id resolves explicit arg, context user, then defaults."""
  tool = SearchMemoryTool(config=config)
  tool_context = SimpleNamespace(user_id="context-user")

  # Explicit user_id beats the tool_context user.
  assert (
      tool._get_user_id("explicit-user", tool_context=tool_context)
      == "explicit-user"
  )

  # The tool_context user beats configured defaults.
  assert tool._get_user_id(None, tool_context=tool_context) == "context-user"

  # Configured defaults still apply with no tool_context.
  assert tool._get_user_id(None) == "alice"

  # An empty context user counts as absent.
  empty_context = SimpleNamespace(user_id="")
  assert tool._get_user_id(None, tool_context=empty_context) == "alice"

  # A context without a user_id attribute falls through safely.
  assert tool._get_user_id(None, tool_context=object()) == "alice"


def test_get_user_id_without_defaults_returns_none():
  """_get_user_id returns None when no source provides a user."""
  tool = SearchMemoryTool(config=MemoryToolConfig())
  assert tool._get_user_id(None, tool_context=object()) is None


@pytest.mark.asyncio
async def test_search_memory_tool_scopes_to_tool_context_user(
    config, fake_client
):
  """SearchMemoryTool scopes search to the ADK tool_context user."""
  tool = SearchMemoryTool(config=config)
  tool_context = SimpleNamespace(user_id="bob")
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"query": "seat"}, tool_context=tool_context
    )

  assert result["status"] == "success"
  assert fake_client.search_request["filter"] == {
      "namespace": {"eq": "test-ns"},
      "ownerId": {"eq": "bob"},
  }


@pytest.mark.asyncio
async def test_create_memory_tool_uses_tool_context_user(config, fake_client):
  """CreateMemoryTool stamps records with the ADK tool_context user."""
  tool = CreateMemoryTool(config=config)
  tool_context = SimpleNamespace(user_id="bob")
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"content": "User likes tea."}, tool_context=tool_context
    )

  assert result["status"] == "success"
  assert fake_client.created_records[0]["ownerId"] == "bob"


@pytest.mark.asyncio
async def test_create_memory_tool_writes_record(config, fake_client):
  """CreateMemoryTool writes a Redis Agent Memory record."""
  assert config.backend == REDIS_AGENT_MEMORY_BACKEND
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"content": "User likes tea."})

  assert result["status"] == "success"
  assert fake_client.created_records[0]["text"] == "User likes tea."
  assert fake_client.created_records[0]["ownerId"] == "alice"
  assert fake_client.created_records[0]["namespace"] == "test-ns"
  assert fake_client.created_records[0]["memoryType"] == "semantic"


@pytest.mark.asyncio
async def test_create_memory_tool_uses_client_supplied_id(config, fake_client):
  """CreateMemoryTool derives a scoped ID from a client-supplied id."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"content": "User likes tea.", "id": "retry-abc-123"}
    )

  assert result["status"] == "success"
  expected_id = stable_memory_id("client", "test-ns", "alice", "retry-abc-123")
  assert result["memory_id"] == expected_id
  assert fake_client.created_records[0]["id"] == expected_id


@pytest.mark.asyncio
async def test_create_memory_tool_preserves_client_id_uniqueness(
    config, fake_client
):
  """Distinct raw client IDs remain distinct after managed-safe mapping."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    await tool.run_async(
        args={"content": "User likes tea.", "id": "retry:abc_123"}
    )
    await tool.run_async(
        args={"content": "User likes tea.", "id": "retry_abc_123"}
    )

  assert (
      fake_client.created_records[0]["id"]
      != fake_client.created_records[1]["id"]
  )


@pytest.mark.asyncio
async def test_create_memory_tool_scopes_client_id(config, fake_client):
  """The same application ID cannot collide across users."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    await tool.run_async(args={"content": "Alice memory", "id": "request-1"})
    await tool.run_async(
        args={
            "content": "Bob memory",
            "id": "request-1",
            "user_id": "bob",
        }
    )

  assert (
      fake_client.created_records[0]["id"]
      != fake_client.created_records[1]["id"]
  )


@pytest.mark.asyncio
async def test_create_memory_tool_treats_zero_as_client_id(config, fake_client):
  """A numeric zero is a supplied client ID, not a missing value."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"content": "User likes tea.", "id": 0})

  expected_id = stable_memory_id("client", "test-ns", "alice", "0")
  assert result["status"] == "success"
  assert fake_client.created_records[0]["id"] == expected_id


@pytest.mark.asyncio
async def test_create_memory_tool_defaults_to_stable_id(config, fake_client):
  """CreateMemoryTool falls back to the stable content-derived ID."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"content": "User likes tea."})

  expected_id = stable_memory_id(
      "tool", "test-ns", "alice", "semantic", "User likes tea."
  )
  assert result["status"] == "success"
  assert fake_client.created_records[0]["id"] == expected_id


@pytest.mark.asyncio
async def test_create_memory_tool_same_id_is_idempotent(config, fake_client):
  """Two calls with the same client id send the same record ID."""
  tool = CreateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    await tool.run_async(args={"content": "First attempt.", "id": "retry-1"})
    await tool.run_async(args={"content": "First attempt.", "id": "retry-1"})

  assert len(fake_client.created_records) == 2
  assert (
      fake_client.created_records[0]["id"]
      == fake_client.created_records[1]["id"]
      == stable_memory_id("client", "test-ns", "alice", "retry-1")
  )


@pytest.mark.asyncio
async def test_search_memory_tool_uses_owner_and_namespace_filter(
    config, fake_client
):
  """SearchMemoryTool scopes search by owner and namespace."""
  tool = SearchMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"query": "seat"})

  assert result["status"] == "success"
  assert fake_client.search_request["filter"] == {
      "namespace": {"eq": "test-ns"},
      "ownerId": {"eq": "alice"},
  }


@pytest.mark.asyncio
async def test_memory_prompt_tool_scopes_to_tool_context_user(
    config, fake_client
):
  """MemoryPromptTool scopes its request to the ADK invocation user."""
  tool = MemoryPromptTool(config=config)

  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"query": "seat"},
        tool_context=SimpleNamespace(user_id="bob"),
    )

  assert result["status"] == "success"
  assert fake_client.search_request["filter"] == {
      "namespace": {"eq": "test-ns"},
      "ownerId": {"eq": "bob"},
  }


@pytest.mark.asyncio
async def test_update_memory_tool_calls_update(config, fake_client):
  """UpdateMemoryTool calls Redis Agent Memory update."""
  tool = UpdateMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"memory_id": "memory-1", "content": "Updated"}
    )

  assert result["status"] == "success"
  assert fake_client.update_kwargs == {
      "memory_id": "memory-1",
      "text": "Updated",
      "namespace": "test-ns",
      "owner_id": "alice",
  }


@pytest.mark.asyncio
async def test_update_memory_tool_scopes_to_tool_context_user(
    config, fake_client
):
  """UpdateMemoryTool verifies and applies the ADK invocation user."""
  tool = UpdateMemoryTool(config=config)
  fake_client.memory_owner_id = "bob"

  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"memory_id": "memory-1", "content": "Updated"},
        tool_context=SimpleNamespace(user_id="bob"),
    )

  assert result["status"] == "success"
  assert fake_client.update_kwargs["owner_id"] == "bob"


@pytest.mark.asyncio
async def test_opensource_update_rejects_memory_owned_by_another_user():
  """Self-hosted updates cannot mutate another invocation user's memory."""
  fake_client = FakeAgentMemoryServerClient()
  fake_client.memory_user_id = "alice"
  config = MemoryToolConfig(
      backend=OPENSOURCE_AGENT_MEMORY_BACKEND,
      default_namespace="test_ns",
  )
  tool = UpdateMemoryTool(config=config)

  with patch.object(
      tool,
      "_get_agent_memory_server_client",
      return_value=fake_client,
  ):
    result = await tool.run_async(
        args={"memory_id": "memory-1", "content": "Updated"},
        tool_context=SimpleNamespace(user_id="bob"),
    )

  assert result["status"] == "error"
  assert "outside the resolved" in result["message"]
  assert fake_client.edit_memory_kwargs is None


@pytest.mark.asyncio
async def test_delete_memory_tool_calls_bulk_delete(config, fake_client):
  """DeleteMemoryTool deletes memory IDs."""
  tool = DeleteMemoryTool(config=config)
  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"memory_ids": ["memory-1"]})

  assert result["status"] == "success"
  assert result["deleted_count"] == 1
  assert fake_client.deleted_ids == ["memory-1"]


@pytest.mark.asyncio
async def test_delete_memory_tool_bounds_preflight_concurrency(
    config, fake_client
):
  """Managed delete preflight reads use bounded concurrency."""
  tool = DeleteMemoryTool(config=config)
  memory_ids = [f"memory-{index}" for index in range(25)]

  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(args={"memory_ids": memory_ids})

  assert result["status"] == "success"
  assert fake_client.max_concurrent_gets == 10
  assert fake_client.deleted_ids == memory_ids


@pytest.mark.asyncio
async def test_opensource_delete_bounds_preflight_concurrency():
  """Self-hosted delete preflight reads use bounded concurrency."""
  fake_client = FakeAgentMemoryServerClient()
  config = MemoryToolConfig(
      backend=OPENSOURCE_AGENT_MEMORY_BACKEND,
      default_namespace="test_ns",
      default_user_id="alice",
  )
  tool = DeleteMemoryTool(config=config)
  memory_ids = [f"memory-{index}" for index in range(25)]

  with patch.object(
      tool,
      "_get_agent_memory_server_client",
      return_value=fake_client,
  ):
    result = await tool.run_async(args={"memory_ids": memory_ids})

  assert result["status"] == "success"
  assert fake_client.max_concurrent_gets == 10
  assert fake_client.deleted_ids == memory_ids


@pytest.mark.asyncio
async def test_delete_memory_tool_rejects_cross_user_ids(config, fake_client):
  """DeleteMemoryTool validates ownership before deleting any memory."""
  tool = DeleteMemoryTool(config=config)
  fake_client.memory_owner_id = "alice"

  with patch.object(tool, "_get_client", return_value=fake_client):
    result = await tool.run_async(
        args={"memory_ids": ["memory-1"]},
        tool_context=SimpleNamespace(user_id="bob"),
    )

  assert result["status"] == "error"
  assert "outside the resolved" in result["message"]
  assert fake_client.deleted_ids == []


@pytest.mark.asyncio
async def test_create_memory_tool_can_use_agent_memory_server_backend():
  """CreateMemoryTool can write through the self-hosted backend."""
  fake_client = FakeAgentMemoryServerClient()
  config = MemoryToolConfig(
      backend=OPENSOURCE_AGENT_MEMORY_BACKEND,
      default_namespace="test_ns",
      default_user_id="alice",
  )
  tool = CreateMemoryTool(config=config)

  with patch.object(
      tool,
      "_get_agent_memory_server_client",
      return_value=fake_client,
  ):
    result = await tool.run_async(args={"content": "User likes tea."})

  assert result["status"] == "success"
  assert fake_client.add_memory_kwargs["text"] == "User likes tea."
  assert fake_client.add_memory_kwargs["namespace"] == "test_ns"
  assert fake_client.add_memory_kwargs["user_id"] == "alice"


@pytest.mark.asyncio
async def test_create_memory_tool_warns_on_client_id_for_self_hosted(caplog):
  """Self-hosted warning explains behavior without exposing the client id."""
  fake_client = FakeAgentMemoryServerClient()
  config = MemoryToolConfig(
      backend=OPENSOURCE_AGENT_MEMORY_BACKEND,
      default_namespace="test_ns",
      default_user_id="alice",
  )
  tool = CreateMemoryTool(config=config)

  with patch.object(
      tool,
      "_get_agent_memory_server_client",
      return_value=fake_client,
  ):
    with caplog.at_level(logging.WARNING, logger="adk_redis"):
      result = await tool.run_async(
          args={"content": "User likes tea.", "id": "retry-abc-123"}
      )

  assert result["status"] == "success"
  assert fake_client.add_memory_kwargs["text"] == "User likes tea."
  assert "retry-abc-123" not in caplog.text
  assert "not supported by the opensource-agent-memory backend" in caplog.text
  assert "Proceeding without the client id" in caplog.text
