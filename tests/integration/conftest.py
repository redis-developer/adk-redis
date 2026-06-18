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

"""Shared fixtures for adk-redis integration tests."""

from __future__ import annotations

import os
import uuid

import pytest

pytest.importorskip("redisvl")
pytest.importorskip("redis")


REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6399")


def _redis_reachable(url: str) -> bool:
  """Return True if a Redis instance with FT module is reachable at url."""
  try:
    import redis

    client = redis.Redis.from_url(url, socket_timeout=1.0)
    client.ping()
    modules = client.module_list()
    names = {
        m[b"name"].decode() if isinstance(m, dict) else m[1] for m in modules
    }
    client.close()
    return "search" in names
  except Exception:
    return False


REDIS_OK = _redis_reachable(REDIS_URL)
REQUIRES_REDIS = pytest.mark.skipif(
    not REDIS_OK,
    reason=(
        f"Redis with FT module not reachable at {REDIS_URL}. "
        "Start one with: docker run -d -p 6399:6379 redis:8.4"
    ),
)


REDIS_AGENT_MEMORY_URL = os.environ.get("REDIS_AGENT_MEMORY_API_BASE_URL")
REDIS_AGENT_MEMORY_API_KEY = os.environ.get(
    "REDIS_AGENT_MEMORY_API_KEY"
) or os.environ.get("AGENT_MEMORY_API_KEY")
REDIS_AGENT_MEMORY_STORE_ID = os.environ.get(
    "REDIS_AGENT_MEMORY_STORE_ID"
) or os.environ.get("AGENT_MEMORY_STORE_ID")

REQUIRES_REDIS_AGENT_MEMORY = pytest.mark.skipif(
    not (
        REDIS_AGENT_MEMORY_URL
        and REDIS_AGENT_MEMORY_API_KEY
        and REDIS_AGENT_MEMORY_STORE_ID
    ),
    reason=(
        "Redis Agent Memory env vars not set. Set "
        "REDIS_AGENT_MEMORY_API_BASE_URL, REDIS_AGENT_MEMORY_API_KEY "
        "(or AGENT_MEMORY_API_KEY), and REDIS_AGENT_MEMORY_STORE_ID "
        "(or AGENT_MEMORY_STORE_ID) to enable."
    ),
)


AGENT_MEMORY_SERVER_URL = os.environ.get("AGENT_MEMORY_SERVER_URL")

REQUIRES_AGENT_MEMORY_SERVER = pytest.mark.skipif(
    not AGENT_MEMORY_SERVER_URL,
    reason=(
        "Agent Memory Server not configured. Set AGENT_MEMORY_SERVER_URL "
        "(for example http://localhost:8000) to enable."
    ),
)


@pytest.fixture(scope="session")
def redis_url() -> str:
  """Redis URL for integration tests."""
  return REDIS_URL


@pytest.fixture
def unique_index_name() -> str:
  """Unique index name to isolate test runs."""
  return f"adk_redis_it_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_namespace() -> str:
  """Unique namespace to isolate memory-backend test runs."""
  return f"adk_redis_it_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_user_id() -> str:
  """Unique owner/user ID to isolate memory-backend test runs."""
  return f"user_{uuid.uuid4().hex[:8]}"
