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

"""End-to-end smoke for examples/redis_sql_search through the ADK Runner.

Loads the product catalog into Redis (idempotent), constructs the example
agent, runs it through `InMemoryRunner.run_async` against the real Gemini
API, and asserts that the LLM called `catalog_sql_search` and got a
non-empty `success` payload back. Prints a transcript so a human can see
the model output too.

Requires:
  - GEMINI_API_KEY (or GOOGLE_API_KEY) in the environment.
  - Redis 8.4 reachable at $REDIS_URL (default redis://localhost:6379).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "redis_sql_search"
sys.path.insert(0, str(EXAMPLE_DIR))

from load_data import load_data  # noqa: E402
from redis_sql_search_agent.agent import root_agent  # noqa: E402


PROMPTS = [
    "What electronics cost less than 100 dollars?",
    "Which products from DeskWorks have a rating of 4.4 or higher?",
]


def _ensure_api_key() -> None:
  if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
    print(
        "ERROR: set GOOGLE_API_KEY or GEMINI_API_KEY in the environment.",
        file=sys.stderr,
    )
    sys.exit(2)
  if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


async def _run_prompt(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    prompt: str,
) -> tuple[list[str], list[tuple[str, dict]], list[tuple[str, dict]]]:
  """Drive one user turn. Return (text_chunks, tool_calls, tool_responses)."""
  text_chunks: list[str] = []
  tool_calls: list[tuple[str, dict]] = []
  tool_responses: list[tuple[str, dict]] = []

  new_message = types.Content(role="user", parts=[types.Part(text=prompt)])
  async for event in runner.run_async(
      user_id=user_id, session_id=session_id, new_message=new_message
  ):
    if not event.content or not event.content.parts:
      continue
    for part in event.content.parts:
      if part.text:
        text_chunks.append(part.text)
      if part.function_call:
        tool_calls.append(
            (part.function_call.name, dict(part.function_call.args or {}))
        )
      if part.function_response:
        tool_responses.append(
            (
                part.function_response.name,
                dict(part.function_response.response or {}),
            )
        )
  return text_chunks, tool_calls, tool_responses


async def main() -> int:
  _ensure_api_key()

  print("=== Loading sample catalog ===")
  load_data()

  print("\n=== Running agent end-to-end ===")
  runner = InMemoryRunner(agent=root_agent, app_name="redis_sql_search_smoke")
  user_id = "smoke-user"
  session = await runner.session_service.create_session(
      app_name=runner.app_name, user_id=user_id
  )

  failures = 0
  for prompt in PROMPTS:
    print(f"\n--- prompt: {prompt}")
    text_chunks, tool_calls, tool_responses = await _run_prompt(
        runner, user_id, session.id, prompt
    )

    print(f"[tool calls]")
    for name, args in tool_calls:
      print(f"  - {name}({json.dumps(args)[:200]})")
    print(f"[tool responses]")
    for name, response in tool_responses:
      brief = {
          "status": response.get("status"),
          "count": response.get("count"),
      }
      print(f"  - {name} -> {brief}")
    print(f"[final text]")
    print("    " + (" ".join(text_chunks).strip()[:800] or "(empty)"))

    tool_names = {name for name, _ in tool_calls}
    if "catalog_sql_search" not in tool_names:
      print("FAIL: agent did not call catalog_sql_search.", file=sys.stderr)
      failures += 1
      continue
    statuses = {r.get("status") for _, r in tool_responses}
    if "success" not in statuses:
      print(
          "FAIL: tool returned no success payload. statuses="
          f"{sorted(s for s in statuses if s)}",
          file=sys.stderr,
      )
      failures += 1

  await runner.close()

  if failures:
    print(f"\n=== smoke FAILED ({failures} prompt(s) failed) ===")
    return 1
  print("\n=== smoke OK ===")
  return 0


if __name__ == "__main__":
  raise SystemExit(asyncio.run(main()))
