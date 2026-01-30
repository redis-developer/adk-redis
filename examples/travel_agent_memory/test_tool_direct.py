#!/usr/bin/env python3
"""Direct test of CreateMemoryTool to debug issues."""

import asyncio

from adk_redis.tools.memory import CreateMemoryTool, MemoryToolConfig

# Configuration
MEMORY_SERVER_URL = "http://localhost:8088"
NAMESPACE = "test_direct"
USER_ID = "test_user"


async def main():
    """Test CreateMemoryTool directly."""
    print("Testing CreateMemoryTool directly\n")
    print(f"Memory Server: {MEMORY_SERVER_URL}")
    print(f"Namespace: {NAMESPACE}")
    print(f"User ID: {USER_ID}\n")

    # Configure memory tool
    config = MemoryToolConfig(
        api_base_url=MEMORY_SERVER_URL,
        default_namespace=NAMESPACE,
        default_user_id=USER_ID,
    )

    # Create tool
    tool = CreateMemoryTool(config=config)

    # Test 1: Call with content
    print("Test 1: Creating memory with content='I like pizza'")
    result = await tool.run_async(content="I like pizza")
    print(f"Result: {result}\n")

    # Test 2: Call without content
    print("Test 2: Creating memory without content")
    result = await tool.run_async()
    print(f"Result: {result}\n")

    # Test 3: Call with all parameters
    print("Test 3: Creating memory with all parameters")
    result = await tool.run_async(
        content="I prefer window seats",
        topics=["travel", "preferences"],
        memory_type="preference",
    )
    print(f"Result: {result}\n")


if __name__ == "__main__":
    asyncio.run(main())

