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
from urllib.parse import urlparse
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


@pytest.fixture
def restricted_acl_url(redis_url: str):
  """Yield a Redis URL for a user granted +@read +@write and no @search.

  This is the credential shape reported by customers whose search indices
  are provisioned by a platform team: FT.INFO and FT.CREATE are denied,
  while FT.SEARCH stays reachable through the @read category on Redis 8.2
  and later. Skips when the server will not provision such a user, or when
  it does not categorize FT.INFO the way this fixture's callers expect.
  """
  import redis

  admin = redis.Redis.from_url(redis_url)
  username = f"acl_probe_{uuid.uuid4().hex[:8]}"
  password = uuid.uuid4().hex
  try:
    admin.execute_command(
        "ACL",
        "SETUSER",
        username,
        "on",
        f">{password}",
        "~*",
        "+@read",
        "+@write",
    )
  except redis.exceptions.ResponseError as e:
    admin.close()
    pytest.skip(f"cannot provision an ACL user on this Redis: {e}")

  parsed = urlparse(redis_url)
  netloc = f"{username}:{password}@{parsed.hostname}"
  if parsed.port:
    netloc = f"{netloc}:{parsed.port}"
  url = parsed._replace(netloc=netloc).geturl()

  try:
    # Older servers and some managed flavors do not put module commands in
    # any ACL category, so confirm the grant actually withholds FT.INFO
    # before a caller asserts on that.
    scoped = redis.Redis.from_url(url)
    try:
      denied = False
      try:
        scoped.execute_command("FT.INFO", "acl_probe_missing_index")
      except redis.exceptions.ResponseError as e:
        # An allowed FT.INFO reports an unknown index instead. redis-py
        # strips the NOPERM prefix, so match on the message body.
        denied = "no permissions" in str(e).lower()
    finally:
      scoped.close()
    if not denied:
      pytest.skip("FT.INFO is not denied by +@read +@write on this Redis")
    yield url
  finally:
    try:
      admin.execute_command("ACL", "DELUSER", username)
    finally:
      admin.close()
