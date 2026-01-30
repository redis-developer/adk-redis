#!/usr/bin/env python3
"""Simple test to verify memory tools work with ADK Runner."""

import asyncio
import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types

from adk_redis.sessions import (
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)
from adk_redis.tools.memory import (
    CreateMemoryTool,
    MemoryToolConfig,
    SearchMemoryTool,
)

# Configuration
MEMORY_SERVER_URL = "http://localhost:8088"
NAMESPACE = "test_tools_simple"
USER_ID = "test_user"


def main():
    """Test memory tools with a simple conversation."""
    print("Testing Memory Tools with ADK Runner\n")
    print(f"Memory Server: {MEMORY_SERVER_URL}")
    print(f"Namespace: {NAMESPACE}")
    print(f"User ID: {USER_ID}\n")

    # Configure memory tools
    config = MemoryToolConfig(
        api_base_url=MEMORY_SERVER_URL,
        default_namespace=NAMESPACE,
        default_user_id=USER_ID,
    )

    # Create only 2 tools for simplicity
    tools = [
        CreateMemoryTool(config=config),
        SearchMemoryTool(config=config),
    ]

    # Configure session service
    session_config = RedisWorkingMemorySessionServiceConfig(
        api_base_url=MEMORY_SERVER_URL,
        default_namespace=NAMESPACE,
    )
    session_service = RedisWorkingMemorySessionService(config=session_config)

    # Create agent with explicit instructions to use tools
    agent = Agent(
        model="gemini-2.5-flash",
        name="test_agent",
        description="Test agent for memory tools",
        tools=tools,
        instruction="""You are a test assistant with memory tools.

IMPORTANT: You MUST use the tools available to you:
- When the user asks you to remember something, use create_memory tool
- When the user asks what you remember, use search_memory tool

ALWAYS use the tools. Do not just acknowledge - actually call the tools.""",
    )

    # Create runner
    runner = Runner(
        agent=agent,
        session_service=session_service,
        app_name=NAMESPACE,
    )

    # Generate session ID
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}\n")

    # Test messages
    messages = [
        "Please remember that I like pizza",
        "What do you remember about me?",
    ]

    for idx, user_message in enumerate(messages, 1):
        print(f"\n{'='*60}")
        print(f"Message {idx}/{len(messages)}")
        print(f"{'='*60}")
        print(f"USER: {user_message}\n")

        message = types.Content(role="user", parts=[types.Part(text=user_message)])

        agent_response = ""
        tool_calls = []

        for event in runner.run(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
        ):
            # Track tool calls
            if hasattr(event, "function_calls") and event.function_calls:
                for fc in event.function_calls:
                    tool_calls.append(fc.name)
                    print(f"  🔧 TOOL CALL: {fc.name}")

            # Get response
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        agent_response = part.text

        if tool_calls:
            print(f"\n  Tools used: {', '.join(tool_calls)}")

        print(f"\nAGENT: {agent_response}\n")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

