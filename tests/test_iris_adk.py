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

"""Exercise the public Iris adapters at the ADK call sites."""

import asyncio
from contextlib import aclosing
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import pytest

iris = pytest.importorskip("adk_redis.iris")
gateway_types = pytest.importorskip("redis_iris.context_gateway")


class _ClinicModel(BaseLlm):
  """Check Playbooks and Gateway reach the model and make a tool call."""

  async def generate_content_async(self, llm_request, stream=False):
    assert (
        "Use the directory {carefully}."
        in llm_request.config.system_instruction
    )
    declaration = llm_request.config.tools[0].function_declarations[0]
    assert declaration.name == "clinic_lookup"
    assert declaration.parameters_json_schema == {
        "type": "object",
        "properties": {"specialty": {"type": "string", "enum": ["cardiology"]}},
        "required": ["specialty"],
        "additionalProperties": False,
    }
    responses = [
        part.function_response
        for content in llm_request.contents
        for part in content.parts or []
        if part.function_response
    ]
    if responses:
      assert responses[-1].response == {"result": {"count": 2}}
      part = types.Part(text="Two cardiologists.")
    else:
      part = types.Part.from_function_call(
          name="clinic_lookup", args={"specialty": "cardiology"}
      )
    yield LlmResponse(content=types.Content(role="model", parts=[part]))


def _message(text: str) -> types.Content:
  return types.Content(role="user", parts=[types.Part(text=text)])


async def test_gateway_and_playbooks_compose_with_a_real_runner():
  schema = {
      "type": "object",
      "properties": {"specialty": {"type": "string", "enum": ["cardiology"]}},
      "required": ["specialty"],
      "additionalProperties": False,
  }
  catalog = [
      gateway_types.GatewayTool("clinic.lookup", "Find clinicians", schema),
      gateway_types.GatewayTool("other_tool", "Another tool", {}),
  ]
  gateway = SimpleNamespace(
      atools=AsyncMock(return_value=catalog),
      acall=AsyncMock(
          return_value=gateway_types.ToolResult(text="", data={"count": 2})
      ),
  )
  hooks = SimpleNamespace(
      abefore=AsyncMock(return_value="Use the directory {carefully}.")
  )
  app = App(
      name="clinic",
      root_agent=Agent(
          name="clinic_agent",
          model=_ClinicModel(model="clinic-test"),
          tools=[
              iris.IrisGatewayToolset(gateway, tool_filter=["clinic_lookup"])
          ],
      ),
      plugins=[iris.IrisPlaybooksPlugin(hooks)],
  )
  sessions = InMemorySessionService()
  await sessions.create_session(app_name="clinic", user_id="u", session_id="s")
  async with Runner(app=app, session_service=sessions) as runner:
    events = [
        event
        async for event in runner.run_async(
            user_id="u", session_id="s", new_message=_message("Find clinicians")
        )
    ]
  assert events[-1].content.parts[0].text == "Two cardiologists."
  gateway.acall.assert_awaited_once_with(
      "clinic.lookup", {"specialty": "cardiology"}
  )
  assert hooks.abefore.await_count == 2
  hooks.abefore.assert_awaited_with("Find clinicians", owner="u", session="s")


async def test_gateway_rejects_colliding_model_aliases():
  gateway = SimpleNamespace(
      atools=AsyncMock(
          return_value=[
              gateway_types.GatewayTool("clinic.lookup", "", {}),
              gateway_types.GatewayTool("clinic_lookup", "", {}),
          ]
      )
  )
  errors = pytest.importorskip("redis_iris.errors")
  with pytest.raises(errors.ConfigurationError, match="both map"):
    await iris.IrisGatewayToolset(gateway).get_tools()


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        (
            [
                SimpleNamespace(
                    target=SimpleNamespace(type="workflow", ref="known")
                )
            ],
            "specialist",
        ),
        (
            [SimpleNamespace(target=SimpleNamespace(type="tool", ref="known"))],
            "fallback",
        ),
        (
            [
                SimpleNamespace(
                    target=SimpleNamespace(type="workflow", ref="unknown")
                )
            ],
            "fallback",
        ),
        ([SimpleNamespace(target=None)], "fallback"),
        ([], "fallback"),
    ],
)
async def test_router_dispatches_only_registered_targets(items, expected):
  client = SimpleNamespace(
      amatch=AsyncMock(return_value=SimpleNamespace(items=items))
  )
  router = iris.IrisIntentRouter(
      {("workflow", "known"): "specialist"}, fallback="fallback", router=client
  )
  assert await router.select("query") == expected
  assert await router.select("  ") == "fallback"
  client.amatch.assert_awaited_once_with("query", limit=1)


@pytest.mark.parametrize(
    ("scenario", "outcome"),
    [
        ("complete", "completed"),
        ("error_event", "failed"),
        ("exception", "failed"),
        ("timeout", "timeout"),
        ("closed", "abandoned"),
        ("cancelled", "abandoned"),
    ],
)
async def test_lens_marks_outcome_and_closes_the_runner(
    monkeypatch, scenario, outcome
):
  from_context = pytest.importorskip("redis_iris.lens")
  turn = MagicMock()
  handle = turn.return_value.__enter__.return_value
  monkeypatch.setattr(from_context, "init", lambda **_: True)
  monkeypatch.setattr(from_context, "turn", turn)
  closed = asyncio.Event()

  async def run(**kwargs):
    assert kwargs["invocation_id"] == "resume"
    try:
      if scenario == "exception":
        raise ValueError("bad run")
      if scenario == "timeout":
        raise TimeoutError()
      if scenario == "cancelled":
        raise asyncio.CancelledError()
      yield Event(
          author="assistant",
          error_code="broken" if scenario == "error_event" else None,
      )
    finally:
      closed.set()

  telemetry = iris.IrisLens(agent_id="agent")
  events = telemetry.run_async(
      SimpleNamespace(run_async=run),
      user_id="u",
      session_id="s",
      invocation_id="resume",
  )
  async with aclosing(events):
    if scenario == "closed":
      await anext(events)
    elif scenario == "exception":
      with pytest.raises(ValueError, match="bad run"):
        await anext(events)
    elif scenario == "timeout":
      with pytest.raises(TimeoutError):
        await anext(events)
    elif scenario == "cancelled":
      with pytest.raises(asyncio.CancelledError):
        await anext(events)
    else:
      assert len([event async for event in events]) == 1
  assert closed.is_set()
  turn.assert_called_once_with("s", user_id="u")
  handle.set_outcome.assert_called_once_with(outcome)


async def test_mesh_emits_text_deltas_then_terminal_message():
  async def run(**kwargs):
    assert kwargs["run_config"].streaming_mode.value == "sse"
    yield Event(
        author="agent",
        partial=True,
        content=types.Content(
            parts=[
                types.Part(text="hidden", thought=True),
                types.Part(text="first"),
            ]
        ),
    )
    yield Event(
        author="agent",
        content=types.Content(parts=[types.Part(text="first second")]),
    )

  writer = SimpleNamespace(append=AsyncMock(), finish=AsyncMock())
  await iris.stream_adk_turn(
      SimpleNamespace(run_async=run),
      writer,
      user_id="u",
      session_id="s",
      message=_message("go"),
  )
  writer.append.assert_awaited_once_with("delta", {"text": "first"})
  writer.finish.assert_awaited_once_with("message", {"text": "first second"})


async def test_mesh_reports_interrupted_turns():
  async def run(**kwargs):
    yield Event(author="agent", long_running_tool_ids={"approval"})

  writer = SimpleNamespace(append=AsyncMock(), finish=AsyncMock())
  await iris.stream_adk_turn(
      SimpleNamespace(run_async=run),
      writer,
      user_id="u",
      session_id="s",
      message=_message("go"),
  )
  writer.append.assert_not_awaited()
  writer.finish.assert_awaited_once_with("turn.interrupted", {})
