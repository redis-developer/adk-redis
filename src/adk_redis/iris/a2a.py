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

"""Serve a Google ADK Runner with Redis Agent Mesh's resumable A2A routes."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from copy import deepcopy

from a2a.server.routes import create_agent_card_routes
from a2a.server.routes import create_jsonrpc_routes
from a2a.types import AgentCard
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.runners import Runner
from redis.asyncio import Redis
from redis.asyncio import RedisCluster
from redis_iris.agent_mesh.a2a import RedisTaskEventStream
from redis_iris.agent_mesh.a2a import RedisTaskStore
from redis_iris.agent_mesh.a2a.routes import create_resumable_rest_routes
from redis_iris.agent_mesh.a2a.routes import resumable_streams_extension
from starlette.applications import Starlette
from starlette.authentication import AuthenticationBackend
from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware


def create_mesh_a2a_app(
    *,
    runner: Runner,
    agent_card: AgentCard,
    commands: Redis | RedisCluster,
    readers: Redis | RedisCluster,
    namespace: str,
    auth_backend: AuthenticationBackend,
) -> Starlette:
  """Build an authenticated A2A app with resumable ADK task streams.

  The caller owns the runner and both Redis clients. Use a dedicated reader
  pool for blocking subscriptions and a session service shared between ADK
  replicas. The authentication backend must populate a stable, unique
  principal as the user's display name. Mesh uses that identity to authorize
  task access, and ADK uses it to scope sessions.
  """
  card = deepcopy(agent_card)
  card.capabilities.streaming = True
  extension = resumable_streams_extension()
  if not any(
      item.uri == extension.uri for item in card.capabilities.extensions
  ):
    card.capabilities.extensions.append(extension)

  store = RedisTaskStore(commands, namespace=namespace)
  stream = RedisTaskEventStream(readers, store=store)
  executor = A2aAgentExecutor(runner=runner, force_new_version=True)
  handler = store.request_handler(
      executor, agent_card=card, event_stream=stream
  )

  @asynccontextmanager
  async def lifespan(_: Starlette) -> AsyncIterator[None]:
    try:
      yield
    finally:
      await handler.aclose()

  return Starlette(
      routes=[
          *create_agent_card_routes(card),
          *create_jsonrpc_routes(handler, rpc_url="/"),
          *create_resumable_rest_routes(
              handler, agent_card=card, store=store, event_stream=stream
          ),
      ],
      middleware=[Middleware(AuthenticationMiddleware, backend=auth_backend)],
      lifespan=lifespan,
  )
