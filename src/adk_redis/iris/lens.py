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

"""Trace Google ADK runs and other turn steps through Redis Lens."""

import asyncio
from collections.abc import AsyncGenerator
from collections.abc import Iterator
from contextlib import aclosing
from contextlib import contextmanager
from typing import Any

from google.adk.events import Event
from google.adk.runners import Runner
from redis_iris import lens


class IrisLens:
  """Trace a complete ADK turn using the process-wide Iris Lens configuration.

  Create this once at application startup and call `shutdown()` at process
  shutdown. Endpoint and key default to the SDK's environment configuration.
  """

  def __init__(
      self,
      *,
      agent_id: str,
      endpoint: str | None = None,
      api_key: str | None = None,
  ) -> None:
    self.enabled: bool = lens.init(
        agent_id=agent_id, endpoint=endpoint, api_key=api_key
    )

  @contextmanager
  def turn(self, *, user_id: str, session_id: str) -> Iterator[str | None]:
    """Trace a turn including steps such as routing before ADK starts."""
    with lens.turn(session_id, user_id=user_id) as trace:
      try:
        yield lens.current_trace_id()
      except (asyncio.CancelledError, GeneratorExit):
        trace.set_outcome("abandoned")
        raise
      except TimeoutError:
        trace.set_outcome("timeout")
        raise
      except Exception:
        trace.set_outcome("failed")
        raise
      else:
        trace.set_outcome("completed")

  async def run_async(
      self,
      runner: Runner,
      *,
      user_id: str,
      session_id: str,
      **run_options: Any,
  ) -> AsyncGenerator[Event, None]:
    """Yield ADK events within a Lens turn.

    Runner options such as `new_message`, `invocation_id` and `run_config`
    are forwarded unchanged. Use `contextlib.aclosing` when breaking out of
    iteration early. An ADK error event is forwarded and marks the trace failed.
    """
    with lens.turn(session_id, user_id=user_id) as trace:
      outcome = "completed"
      try:
        async with aclosing(
            runner.run_async(
                user_id=user_id, session_id=session_id, **run_options
            )
        ) as events:
          async for event in events:
            if event.error_code:
              outcome = "failed"
            yield event
      except (asyncio.CancelledError, GeneratorExit):
        if outcome == "completed":
          outcome = "abandoned"
        raise
      except TimeoutError:
        outcome = "timeout"
        raise
      except Exception:
        outcome = "failed"
        raise
      finally:
        trace.set_outcome(outcome)

  @staticmethod
  def shutdown() -> bool:
    """Flush the process-wide Lens exporter."""
    return bool(lens.shutdown())
