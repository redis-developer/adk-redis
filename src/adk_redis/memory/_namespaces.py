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

"""Namespace name resolution for Redis Agent Memory.

Redis Agent Memory 1.0 stores namespaces as server resources identified by
an ID of the form ``ns_<32 hex>``. adk-redis configuration names namespaces
by a plain name, so each name maps to a shared root namespace of that name.
Names are resolved on each operation because they can be reassigned.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from adk_redis.memory._utils import is_conflict_error
from adk_redis.memory._utils import read_field

logger = logging.getLogger(__name__)

_NAMESPACE_ID_RE = re.compile(r"^ns_[0-9a-f]{32}$")
_LIST_PAGE_SIZE = 200


def is_namespace_id(value: str) -> bool:
  """Return True when a value is already a Redis Agent Memory namespace ID."""
  return bool(_NAMESPACE_ID_RE.fullmatch(value))


def _namespace_id(namespace: object) -> str:
  """Read the required ID from a namespace returned by Iris."""
  value = read_field(namespace, "namespace_id")
  if not isinstance(value, str) or not is_namespace_id(value):
    raise ValueError("Iris returned an invalid namespace ID")
  return value


async def _find_shared_root(agent_memory: Any, name: str) -> str | None:
  """Return the ID of the active shared root namespace called ``name``."""
  cursor = None
  while True:
    response = await agent_memory.list_namespaces_async(
        scope="SHARED",
        limit=_LIST_PAGE_SIZE,
        cursor=cursor,
    )
    for namespace in read_field(response, "items", []) or []:
      if read_field(namespace, "name") != name:
        continue
      if read_field(namespace, "parent_id"):
        continue
      state = read_field(namespace, "state")
      if str(getattr(state, "value", state)) != "ACTIVE":
        raise ValueError(
            f"Namespace '{name}' is archived. Please"
            " configure a different namespace."
        )
      return _namespace_id(namespace)
    cursor = read_field(response, "next_cursor")
    if not cursor:
      return None


async def resolve_namespace_id(
    agent_memory: Any,
    *,
    name: str,
    create: bool,
) -> str | None:
  """Resolve a namespace name to its Redis Agent Memory namespace ID.

  A value that is already a namespace ID is returned unchanged. Otherwise the
  active shared root namespace with that name is looked up, and created when
  ``create`` is True and none exists.

  Args:
      agent_memory: An open Redis Agent Memory SDK client.
      name: Namespace name, or a namespace ID.
      create: Create the namespace when it does not exist. Pass False for
          names that come from model output, so a prompt cannot create
          namespaces.

  Returns:
      The namespace ID, or None when it does not exist and ``create`` is
      False.

  Raises:
      ValueError: If the namespace exists but is archived.
  """
  if is_namespace_id(name):
    return name

  namespace_id = await _find_shared_root(agent_memory, name)
  if namespace_id is not None or not create:
    return namespace_id

  try:
    response = await agent_memory.create_namespace_async(
        request={"name": name, "scope": "SHARED"}
    )
  except Exception as exc:
    if not is_conflict_error(exc):
      raise
    # Another process may have created the namespace since the lookup.
    namespace_id = await _find_shared_root(agent_memory, name)
    if namespace_id is None:
      raise
    return namespace_id

  namespace_id = _namespace_id(read_field(response, "namespace"))
  logger.info("Created shared namespace '%s' (%s)", name, namespace_id)
  return namespace_id
