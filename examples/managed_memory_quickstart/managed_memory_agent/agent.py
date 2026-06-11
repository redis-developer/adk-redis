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

"""Minimal agent using managed Redis Agent Memory services."""

from datetime import datetime

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import load_memory
from google.adk.tools import preload_memory


def before_agent(callback_context: CallbackContext):
  """Update state before the agent runs."""
  callback_context.state["_time"] = datetime.now().isoformat()


async def after_agent(callback_context: CallbackContext):
  """Persist session events to long-term memory after each turn."""
  await callback_context.add_session_to_memory()


root_agent = Agent(
    model="gemini-2.5-flash",
    name="managed_memory_agent",
    description=(
        "Minimal agent with managed Redis Agent Memory session and"
        " long-term memory services."
    ),
    before_agent_callback=before_agent,
    after_agent_callback=after_agent,
    instruction="""You are a helpful assistant with Redis Agent Memory.

## Memory

1. **Working memory**: The current conversation is stored in your session.
2. **Long-term memory**: Use `load_memory` to search facts from past sessions.
   `preload_memory` may surface relevant memories automatically.

## Guidelines

- Be conversational and remember details the user shares.
- When users share personal info, acknowledge it clearly.
- If a memory search returns nothing, say so and ask a clarifying question.

Current time: {_time}""",
    tools=[preload_memory, load_memory],
)
