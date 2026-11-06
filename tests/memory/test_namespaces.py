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

"""Tests for Redis Agent Memory namespace resolution."""

from types import SimpleNamespace

import pytest

from adk_redis.memory._namespaces import resolve_namespace_id
from tests.agent_memory_fakes import FakeNamespaces
from tests.agent_memory_fakes import namespace_id_for


class CountingNamespaces(FakeNamespaces):
  """Fake client that counts namespace listings."""

  def __init__(self, *names):
    self.init_namespaces(*names)
    self.list_calls = 0

  async def list_namespaces_async(self, **kwargs):
    self.list_calls += 1
    return await super().list_namespaces_async(**kwargs)


async def _resolve(client, name, *, create, store_id="store-1"):
  return await resolve_namespace_id(
      client,
      server_url="https://memory.example",
      store_id=store_id,
      name=name,
      create=create,
  )


@pytest.mark.asyncio
async def test_resolves_existing_namespace_without_creating():
  client = CountingNamespaces("travel")

  namespace_id = await _resolve(client, "travel", create=True)

  assert namespace_id == namespace_id_for("travel")
  assert client.created_namespaces == []


@pytest.mark.asyncio
async def test_creates_missing_shared_root_and_caches_it():
  client = CountingNamespaces()

  first = await _resolve(client, "travel", create=True)
  second = await _resolve(client, "travel", create=True)

  assert first == second == namespace_id_for("travel")
  assert client.created_namespaces == [{"name": "travel", "scope": "SHARED"}]
  assert client.list_calls == 1


@pytest.mark.asyncio
async def test_cache_is_scoped_to_the_store():
  client = CountingNamespaces("travel")

  await _resolve(client, "travel", create=True, store_id="store-1")
  await _resolve(client, "travel", create=True, store_id="store-2")

  assert client.list_calls == 2


@pytest.mark.asyncio
async def test_lookup_only_returns_none_for_missing_namespace():
  client = CountingNamespaces()

  assert await _resolve(client, "travel", create=False) is None
  assert client.created_namespaces == []


@pytest.mark.asyncio
async def test_namespace_id_is_used_as_given():
  client = CountingNamespaces()
  namespace_id = "ns_" + "0" * 32

  assert await _resolve(client, namespace_id, create=True) == namespace_id
  assert client.list_calls == 0


@pytest.mark.asyncio
async def test_conflict_on_create_falls_back_to_lookup():
  class RacingClient(CountingNamespaces):
    """Another process creates the namespace between lookup and create."""

    async def create_namespace_async(self, *, request):
      self.namespaces[request["name"]] = namespace_id_for(request["name"])
      error = RuntimeError("conflict")
      error.status_code = 409  # type: ignore[attr-defined]
      raise error

  client = RacingClient()

  assert await _resolve(client, "travel", create=True) == namespace_id_for(
      "travel"
  )


@pytest.mark.asyncio
async def test_archived_namespace_raises():
  class ArchivedClient(FakeNamespaces):

    async def list_namespaces_async(self, **kwargs):
      return SimpleNamespace(
          items=[
              SimpleNamespace(
                  namespace_id=namespace_id_for("travel"),
                  name="travel",
                  parent_id=None,
                  state="ARCHIVED",
              )
          ],
          next_cursor=None,
      )

  client = ArchivedClient()
  client.init_namespaces()

  with pytest.raises(ValueError, match="archived"):
    await _resolve(client, "travel", create=True)


@pytest.mark.asyncio
async def test_lookup_follows_cursor_and_skips_children():
  class PagedClient(FakeNamespaces):

    def __init__(self):
      self.init_namespaces()
      self.cursors = []

    async def list_namespaces_async(self, *, scope, limit, cursor):
      self.cursors.append(cursor)
      if cursor is None:
        child = SimpleNamespace(
            namespace_id=namespace_id_for("child"),
            name="travel",
            parent_id=namespace_id_for("parent"),
            state="ACTIVE",
        )
        return SimpleNamespace(items=[child], next_cursor="page-2")
      root = SimpleNamespace(
          namespace_id=namespace_id_for("travel"),
          name="travel",
          parent_id=None,
          state="ACTIVE",
      )
      return SimpleNamespace(items=[root], next_cursor=None)

  client = PagedClient()

  assert await _resolve(client, "travel", create=False) == namespace_id_for(
      "travel"
  )
  assert client.cursors == [None, "page-2"]
