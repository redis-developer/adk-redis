#!/usr/bin/env python3
"""Simple demo of memory tools without requiring Redis for sessions.

This demonstrates the 5 memory tools by directly calling them,
showing their inputs and outputs clearly.

Requirements:
- Agent Memory Server running on http://localhost:8000
- GOOGLE_API_KEY environment variable set
"""

import asyncio
import os
from datetime import datetime

from adk_redis.tools.memory import (
    CreateMemoryTool,
    DeleteMemoryTool,
    MemoryPromptTool,
    MemoryToolConfig,
    SearchMemoryTool,
    UpdateMemoryTool,
)


async def main():
    """Demonstrate memory tools with a travel agent scenario."""
    
    # Configuration
    MEMORY_SERVER_URL = os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")
    NAMESPACE = "travel_demo"
    USER_ID = "alice"
    
    print("=" * 80)
    print("MEMORY TOOLS DEMONSTRATION")
    print("=" * 80)
    print(f"Memory Server: {MEMORY_SERVER_URL}")
    print(f"Namespace: {NAMESPACE}")
    print(f"User ID: {USER_ID}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create tool instances
    config = MemoryToolConfig(
        api_base_url=MEMORY_SERVER_URL,
        default_namespace=NAMESPACE,
        default_user_id=USER_ID,
    )
    
    create_tool = CreateMemoryTool(config=config)
    search_tool = SearchMemoryTool(config=config)
    update_tool = UpdateMemoryTool(config=config)
    delete_tool = DeleteMemoryTool(config=config)
    prompt_tool = MemoryPromptTool(config=config)
    
    # Demo 1: Create memories
    print("\n" + "─" * 80)
    print("DEMO 1: Creating Travel Preferences")
    print("─" * 80)
    
    memories_created = []
    
    preferences = [
        ("I prefer window seats on flights", ["travel", "flights", "seating"]),
        ("I'm vegetarian", ["food", "dietary", "preferences"]),
        ("I prefer boutique hotels", ["accommodation", "hotels"]),
        ("I have a fear of flying, prefer direct flights", ["travel", "flights", "anxiety"]),
    ]
    
    for content, topics in preferences:
        print(f"\n📝 Creating memory: '{content}'")
        print(f"   Topics: {topics}")
        
        result = await create_tool.run_async(
            content=content,
            topics=topics,
            memory_type="preference",
        )
        
        print(f"   ✅ Result: {result['status']}")
        print(f"   Memory ID: {result['memory_id']}")
        memories_created.append(result['memory_id'])
    
    # Demo 2: Search memories
    print("\n" + "─" * 80)
    print("DEMO 2: Searching Memories")
    print("─" * 80)
    
    queries = [
        "What are my flight preferences?",
        "What are my dietary restrictions?",
        "Tell me about my hotel preferences",
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        
        result = await search_tool.run_async(query=query, limit=3)
        
        print(f"   Found {result['count']} memories:")
        for i, memory in enumerate(result['memories'], 1):
            print(f"   {i}. {memory['content']} (score: {memory['score']:.3f})")
            print(f"      Topics: {memory['topics']}")
    
    # Demo 3: Enrich prompt with memories
    print("\n" + "─" * 80)
    print("DEMO 3: Enriching Prompt with Memories")
    print("─" * 80)
    
    user_query = "I'm planning a trip to Paris. Help me find flights and hotels."
    print(f"\n💬 User query: '{user_query}'")
    
    result = await prompt_tool.run_async(
        query=user_query,
        system_prompt="You are a helpful travel agent.",
    )
    
    print(f"\n✅ Enriched prompt created!")
    print(f"   Memories used: {result['memories_used']}")
    print(f"\n📄 Enriched prompt:")
    print("   " + result['enriched_prompt'].replace("\n", "\n   "))
    
    # Demo 4: Update a memory
    print("\n" + "─" * 80)
    print("DEMO 4: Updating a Memory")
    print("─" * 80)
    
    if memories_created:
        memory_id = memories_created[0]  # Update the first memory
        new_content = "I prefer aisle seats on flights for easier bathroom access"
        
        print(f"\n✏️  Updating memory {memory_id}")
        print(f"   New content: '{new_content}'")
        
        result = await update_tool.run_async(
            memory_id=memory_id,
            content=new_content,
            topics=["travel", "flights", "seating", "accessibility"],
        )
        
        print(f"   ✅ Result: {result['status']}")
        print(f"   {result['message']}")
    
    # Demo 5: Delete memories
    print("\n" + "─" * 80)
    print("DEMO 5: Deleting Memories")
    print("─" * 80)
    
    if len(memories_created) >= 2:
        to_delete = memories_created[2:3]  # Delete the boutique hotel preference
        
        print(f"\n🗑️  Deleting {len(to_delete)} memory(ies)")
        print(f"   IDs: {to_delete}")
        
        result = await delete_tool.run_async(memory_ids=to_delete)
        
        print(f"   ✅ Result: {result['status']}")
        print(f"   Deleted: {result['deleted_count']} memories")
        print(f"   {result['message']}")
    
    # Final search to show updated state
    print("\n" + "─" * 80)
    print("FINAL: Current Memory State")
    print("─" * 80)
    
    result = await search_tool.run_async(query="travel preferences", limit=10)
    
    print(f"\n📊 Total memories: {result['count']}")
    for i, memory in enumerate(result['memories'], 1):
        print(f"{i}. {memory['content']}")
        print(f"   ID: {memory['id']}, Topics: {memory['topics']}")
    
    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

