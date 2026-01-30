# Copyright 2025 Google LLC
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

"""Example: Memory management WITH explicit memory tools (tool-based approach).

This example demonstrates using memory tools where the LLM explicitly controls
memory operations through tool calls. The user can ask the agent to remember,
recall, update, or forget information.
"""

import asyncio
import os
import time

from google.adk.agents import Agent
from google.adk.runners import Runner

from adk_redis.tools.memory import (
    CreateMemoryTool,
    DeleteMemoryTool,
    MemoryPromptTool,
    MemoryToolConfig,
    SearchMemoryTool,
    UpdateMemoryTool,
)
from metrics import ConversationMetrics
from shared_scenarios import get_all_messages

# Configuration
MEMORY_SERVER_URL = os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")
NAMESPACE = "memory_comparison_with_tools"
USER_ID = "alice_123"


async def run_with_tools(messages: list[str]) -> ConversationMetrics:
    """Run conversation using explicit memory tools."""
    metrics = ConversationMetrics(approach="tool-based")

    # Configure memory tools
    config = MemoryToolConfig(
        api_base_url=MEMORY_SERVER_URL,
        default_namespace=NAMESPACE,
        default_user_id=USER_ID,
        recency_boost=True,
    )

    # Create all memory tools
    tools = [
        MemoryPromptTool(config=config),
        SearchMemoryTool(config=config),
        CreateMemoryTool(config=config),
        DeleteMemoryTool(config=config),
        UpdateMemoryTool(config=config),
    ]

    # Create agent with memory tools
    agent = Agent(
        model="gemini-2.0-flash-exp",
        name="memory_agent_with_tools",
        description="Agent with explicit memory tool control",
        tools=tools,
        instruction="""You are a helpful assistant with explicit memory management capabilities.

You have access to memory tools that allow you to:
- search_memory: Search for information you've stored about the user
- create_memory: Store new information when the user shares something or asks you to remember
- update_memory: Modify existing memories when information changes
- delete_memory: Remove memories when the user asks you to forget something
- memory_prompt: Enrich your responses with relevant memories

Guidelines:
1. When the user shares personal information, use create_memory to store it
2. When asked "what do you know about me?" or similar, use search_memory
3. When the user corrects information, use update_memory
4. When asked to forget something, use delete_memory
5. Be explicit about memory operations - tell the user when you store/update/delete information
6. Use memory_prompt to provide personalized context in your responses
""",
    )

    runner = Runner(agent=agent)

    # Process each message
    for user_message in messages:
        print(f"\n{'='*60}")
        print(f"USER: {user_message}")
        print(f"{'='*60}")

        start_time = time.time()

        # Send message and get response
        response = await runner.run(user_message)
        agent_response = response.text

        latency = time.time() - start_time

        print(f"AGENT: {agent_response}")

        # Record metrics
        metrics.record_message(user_message, agent_response, latency)

        # Estimate LLM calls and tokens (simplified)
        metrics.record_llm_call(
            input_tokens=len(user_message.split()) * 2,
            output_tokens=len(agent_response.split()) * 2,
        )

    return metrics


async def main():
    """Main entry point."""
    print("Starting Memory Tools Comparison - WITH TOOLS (Tool-based)")
    print(f"Memory Server: {MEMORY_SERVER_URL}")
    print(f"Namespace: {NAMESPACE}")
    print(f"User ID: {USER_ID}\n")

    messages = get_all_messages()
    metrics = await run_with_tools(messages)

    metrics.print_summary()

    return metrics


if __name__ == "__main__":
    asyncio.run(main())

