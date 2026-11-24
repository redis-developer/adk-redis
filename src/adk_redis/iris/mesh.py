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

"""Publish Google ADK turn events to Redis Agent Mesh FastAPI SSE."""

from contextlib import aclosing
from typing import Protocol

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.genai import types


class _StreamWriter(Protocol):

  async def append(self, type: str, data: dict[str, str], /) -> str:
    ...

  async def finish(self, type: str, data: dict[str, str], /) -> str:
    ...


async def stream_adk_turn(
    runner: Runner,
    writer: _StreamWriter,
    *,
    user_id: str,
    session_id: str,
    message: types.Content,
    run_config: RunConfig | None = None,
) -> None:
  """Publish text deltas and one terminal message via a Mesh StreamWriter.

  The application creates and authorizes the ADK session and stream scope.
  Start this coroutine through the Mesh backend so it can outlive the reader.
  Thought text and tool payloads stay out of the transport.
  """
  config = RunConfig.model_validate({"streaming_mode": "sse"})
  if run_config is not None:
    config = run_config.model_copy(
        update={"streaming_mode": config.streaming_mode}
    )
  answer = ""
  interrupted = False
  async with aclosing(
      runner.run_async(
          user_id=user_id,
          session_id=session_id,
          new_message=message,
          run_config=config,
      )
  ) as events:
    async for event in events:
      if event.error_code:
        raise RuntimeError(f"ADK returned {event.error_code}")
      if event.interrupted or event.long_running_tool_ids:
        interrupted = True
      if event.content is None:
        continue
      text = "".join(
          part.text or ""
          for part in event.content.parts or []
          if not part.thought
      )
      if event.partial:
        if text:
          await writer.append("delta", {"text": text})
      elif event.is_final_response() and text:
        answer = text
  if interrupted:
    await writer.finish("turn.interrupted", {})
    return
  if not answer:
    raise RuntimeError("ADK returned no final text")
  await writer.finish("message", {"text": answer})
