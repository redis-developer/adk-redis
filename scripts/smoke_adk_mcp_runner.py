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

"""End-to-end smoke for examples/redisvl_mcp_search through the ADK Runner.

Requires a running `rvl mcp` server reachable at $REDISVL_MCP_URL
(default http://127.0.0.1:8765/mcp). Start it with:

  REDIS_URL=redis://localhost:6379 rvl mcp \\
    --config examples/redisvl_mcp_search/mcp_config.yaml \\
    --transport streamable-http --host 127.0.0.1 --port 8765

Then run this script with GOOGLE_API_KEY or GEMINI_API_KEY set. The
script drives the agent through one user turn, confirms the LLM called
the MCP `search-records` tool, and prints the transcript.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "redisvl_mcp_search"
sys.path.insert(0, str(EXAMPLE_DIR))

from load_data import load_data  # noqa: E402
from redisvl_mcp_search_agent.agent import root_agent  # noqa: E402

PROMPTS = [
    # Use a keyword-friendly prompt so the BM25 tokenizer matches cleanly.
    # The corpus uses words like 'hybrid', 'caching', 'memory'.
    "Find articles about hybrid search.",
]


def _ensure_api_key() -> None:
  if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
    print(
        "ERROR: set GOOGLE_API_KEY or GEMINI_API_KEY.",
        file=sys.stderr,
    )
    sys.exit(2)
  if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


async def main() -> int:
  _ensure_api_key()

  print("=== Loading sample articles ===")
  load_data()

  print("\n=== Running MCP-backed agent end-to-end ===")
  runner = InMemoryRunner(
      agent=root_agent, app_name="redisvl_mcp_search_smoke"
  )
  user_id = "smoke-user"
  session = await runner.session_service.create_session(
      app_name=runner.app_name, user_id=user_id
  )

  failures = 0
  for prompt in PROMPTS:
    print(f"\n--- prompt: {prompt}")
    new_message = types.Content(role="user", parts=[types.Part(text=prompt)])

    text_chunks: list[str] = []
    tool_calls: list[tuple[str, dict]] = []
    tool_responses: list[tuple[str, dict]] = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=new_message
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

    print("[tool calls]")
    for name, args in tool_calls:
      print(f"  - {name}({json.dumps(args)[:200]})")
    print("[tool responses]")
    for name, response in tool_responses:
      preview = json.dumps(response, default=str)[:1000]
      print(f"  - {name} -> {preview}")
    print("[final text]")
    print("    " + (" ".join(text_chunks).strip()[:800] or "(empty)"))

    tool_names = {name for name, _ in tool_calls}
    if "search-records" not in tool_names:
      print("FAIL: agent did not call search-records.", file=sys.stderr)
      failures += 1
      continue
    # The MCP tool returns structuredContent.results when there are hits.
    saw_results = False
    for _, response in tool_responses:
      structured = response.get("structuredContent") or {}
      if structured.get("results"):
        saw_results = True
        break
    if not saw_results:
      print(
          "FAIL: search-records returned no results for a prompt the "
          "corpus should match.",
          file=sys.stderr,
      )
      failures += 1

  await runner.close()

  if failures:
    print(f"\n=== smoke FAILED ({failures}) ===")
    return 1
  print("\n=== smoke OK ===")
  return 0


if __name__ == "__main__":
  raise SystemExit(asyncio.run(main()))
