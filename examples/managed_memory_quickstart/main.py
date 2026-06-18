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

"""Managed Redis Agent Memory quickstart.

Registers RedisWorkingMemorySessionService and RedisLongTermMemoryService
against the managed redis-agent-memory backend, then serves the agent via ADK's
FastAPI runner.
"""

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.cli.service_registry import get_service_registry
import uvicorn

from adk_redis import REDIS_AGENT_MEMORY_BACKEND
from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig
from adk_redis.sessions import RedisWorkingMemorySessionService
from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig

load_dotenv()

_BACKEND = REDIS_AGENT_MEMORY_BACKEND


def _api_base_url() -> str:
  return os.environ["REDIS_AGENT_MEMORY_API_BASE_URL"]


def parse_base_url(uri: str) -> str:
  """Parse a service URI to extract the base URL."""
  parsed = urlparse(uri)
  location = parsed.netloc + parsed.path
  return (
      location
      if location.startswith(("http://", "https://"))
      else f"http://{location}"
  )


def redis_session_factory(uri: str, **kwargs):
  """Factory for RedisWorkingMemorySessionService."""
  base_url = parse_base_url(uri)
  config = RedisWorkingMemorySessionServiceConfig(
      backend=_BACKEND,
      api_base_url=base_url,
      api_key=os.environ["REDIS_AGENT_MEMORY_API_KEY"],
      store_id=os.environ["REDIS_AGENT_MEMORY_STORE_ID"],
      default_namespace=os.getenv(
          "REDIS_MEMORY_NAMESPACE", "managed_memory_quickstart"
      ),
  )
  return RedisWorkingMemorySessionService(config=config)


def redis_memory_factory(uri: str, **kwargs):
  """Factory for RedisLongTermMemoryService."""
  base_url = parse_base_url(uri)
  config = RedisLongTermMemoryServiceConfig(
      backend=_BACKEND,
      api_base_url=base_url,
      api_key=os.environ["REDIS_AGENT_MEMORY_API_KEY"],
      store_id=os.environ["REDIS_AGENT_MEMORY_STORE_ID"],
      default_namespace=os.getenv(
          "REDIS_MEMORY_NAMESPACE", "managed_memory_quickstart"
      ),
      search_top_k=int(os.getenv("REDIS_MEMORY_SEARCH_TOP_K", "5")),
  )
  return RedisLongTermMemoryService(config=config)


registry = get_service_registry()
registry.register_session_service("redis-working-memory", redis_session_factory)
registry.register_memory_service("redis-long-term-memory", redis_memory_factory)

api_host = _api_base_url().replace("http://", "").replace("https://", "")
SESSION_SERVICE_URI = f"redis-working-memory://{api_host}"
MEMORY_SERVICE_URI = f"redis-long-term-memory://{api_host}"

app: FastAPI = get_fast_api_app(
    agents_dir=".",
    session_service_uri=SESSION_SERVICE_URI,
    memory_service_uri=MEMORY_SERVICE_URI,
    web=True,
    auto_create_session=True,
)


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 8080))
  namespace = os.getenv("REDIS_MEMORY_NAMESPACE", "managed_memory_quickstart")

  print(
      f"""
Starting Managed Redis Agent Memory Quickstart (adk-redis)
==========================================================
ADK Server:     http://localhost:{port}
Memory Backend: {_BACKEND}
API Base URL:   {_api_base_url()}
Store ID:       {os.environ["REDIS_AGENT_MEMORY_STORE_ID"]}
Namespace:      {namespace}

Services:
  - Session: RedisWorkingMemorySessionService
  - Memory:  RedisLongTermMemoryService
"""
  )
  uvicorn.run(app, host="0.0.0.0", port=port)
