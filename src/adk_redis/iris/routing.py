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

"""Resolve Iris Intent Router targets to application-owned ADK dispatch values."""

from collections.abc import Mapping
from typing import Generic, TypeVar

from redis_iris.intent_router import IntentRouter

T = TypeVar("T")


class IrisIntentRouter(Generic[T]):
  """Map the best match to an allowlisted target, such as an ADK Runner.

  The application keys its routes by `(target.type, target.ref)`. The
  configured fallback handles empty messages, unmatched intents, and unknown
  or missing targets. Iris request failures propagate to the caller.

  Args:
      routes: Application-owned target registry.
      fallback: Dispatch value for requests without a registered target.
      router: An SDK client with caller-managed lifetime. Defaults to a fresh
          connection from the Iris environment per lookup.
  """

  def __init__(
      self,
      routes: Mapping[tuple[str, str], T],
      *,
      fallback: T,
      router: IntentRouter | None = None,
  ) -> None:
    self._routes = dict(routes)
    self._fallback = fallback
    self._router = router

  async def select(self, message: str) -> T:
    """Return the registered target for the best matching intent."""
    if not message.strip():
      return self._fallback
    if self._router is None:
      async with IntentRouter.from_env() as router:
        matches = await router.amatch(message, limit=1)
    else:
      matches = await self._router.amatch(message, limit=1)
    target = matches.items[0].target if matches.items else None
    if target is None:
      return self._fallback
    return self._routes.get((target.type, target.ref), self._fallback)
