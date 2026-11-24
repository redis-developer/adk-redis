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

"""Verify Mesh A2A replay and task ownership through the HTTP binding."""

import json
from uuid import uuid4

from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
import pytest
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from starlette.authentication import AuthCredentials
from starlette.authentication import AuthenticationBackend
from starlette.authentication import SimpleUser
from starlette.testclient import TestClient

from tests.integration.conftest import REQUIRES_REDIS

a2a_types = pytest.importorskip("a2a.types")
a2a_context = pytest.importorskip("a2a.server.context")
a2a_routes = pytest.importorskip("a2a.server.routes.common")
mesh = pytest.importorskip("redis_iris.agent_mesh.a2a")
adapter = pytest.importorskip("adk_redis.iris.a2a")

pytestmark = REQUIRES_REDIS


class _TestAuth(AuthenticationBackend):

  async def authenticate(self, conn):
    token = conn.headers.get("Authorization")
    identities = {"Bearer owner-token": "owner", "Bearer other-token": "other"}
    if token in identities:
      return AuthCredentials(["authenticated"]), SimpleUser(identities[token])
    return None


class _TestModel(BaseLlm):
  calls: int = 0

  async def generate_content_async(self, llm_request, stream=False):
    self.calls += 1
    yield LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text="Clinic A")])
    )


def test_a2a_replays_retained_adk_updates_for_the_authenticated_owner(
    redis_url,
):
  with Redis.from_url(redis_url) as redis:
    version = redis.info("server")["redis_version"]
  if tuple(map(int, version.split("-")[0].split(".")[:3])) < (8, 6, 2):
    pytest.skip("Agent Mesh A2A requires Redis 8.6.2+ with XADD IDMP")

  model = _TestModel(model="test-model")
  runner = InMemoryRunner(
      agent=Agent(name="clinic", model=model), app_name="a2a_test"
  )
  commands = AsyncRedis.from_url(redis_url)
  readers = AsyncRedis.from_url(redis_url)
  namespace = f"adk:test:{uuid4().hex}"
  app = adapter.create_mesh_a2a_app(
      runner=runner,
      agent_card=a2a_types.AgentCard(
          name="clinic",
          description="Clinic assistant",
          version="1.0",
          default_input_modes=["text/plain"],
          default_output_modes=["text/plain"],
          skills=[
              a2a_types.AgentSkill(
                  id="clinic",
                  name="Clinic",
                  description="Find clinics",
                  tags=["clinic"],
              )
          ],
          supported_interfaces=[
              a2a_types.AgentInterface(
                  url="http://testserver",
                  protocol_binding="HTTP+JSON",
                  protocol_version="1.0",
              )
          ],
      ),
      commands=commands,
      readers=readers,
      namespace=namespace,
      auth_backend=_TestAuth(),
  )
  headers = {
      "A2A-Version": "1.0",
      "Authorization": "Bearer owner-token",
      "Accept": "text/event-stream",
  }
  task_id = None
  with TestClient(app) as client:
    try:
      card = client.get("/.well-known/agent-card.json")
      assert card.json()["capabilities"]["streaming"]
      reply = client.post(
          "/message:stream",
          headers=headers,
          json={
              "message": {
                  "messageId": uuid4().hex,
                  "role": "ROLE_USER",
                  "parts": [{"text": "Which clinic?"}],
              }
          },
      )
      assert reply.status_code == 200, reply.text
      lines = reply.text.splitlines()
      cursor = next(
          line.removeprefix("id: ") for line in lines if line.startswith("id: ")
      )
      first = next(
          line.removeprefix("data: ")
          for line in lines
          if line.startswith("data: ")
      )
      task_id = json.loads(first)["task"]["id"]
      endpoint = f"/tasks/{task_id}:subscribe"
      headers["Last-Event-ID"] = cursor
      replay = client.get(endpoint, headers=headers)
      assert replay.status_code == 200
      assert f"id: {cursor}" not in replay.text.splitlines()
      assert "Clinic A" in replay.text
      assert "TASK_STATE_COMPLETED" in replay.text
      foreign = client.get(
          endpoint, headers=headers | {"Authorization": "Bearer other-token"}
      )
      assert foreign.status_code == 404
      assert model.calls == 1
    finally:
      if task_id is not None:
        store = mesh.RedisTaskStore(commands, namespace=namespace)
        owner = a2a_routes.StarletteUser(SimpleUser("owner"))
        client.portal.call(
            store.delete, task_id, a2a_context.ServerCallContext(user=owner)
        )
      client.portal.call(runner.close)
      client.portal.call(readers.aclose)
      client.portal.call(commands.aclose)
