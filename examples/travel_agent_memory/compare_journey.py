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

"""Compare travel agent implementations side-by-side."""

import asyncio

from travel_agent_with_tools import run_travel_agent_with_tools
from travel_agent_without_tools import run_travel_agent_without_tools


async def compare_approaches():
    """Run both approaches and compare."""
    print("\n" + "🚀 "*40)
    print("RUNNING TRAVEL AGENT COMPARISON")
    print("🚀 "*40 + "\n")

    # Run with tools
    print("\n📍 PART 1: Running WITH Memory Tools (Explicit Control)\n")
    with_tools_log = await run_travel_agent_with_tools()

    print("\n\n" + "⏸️  "*40)
    print("Pausing 3 seconds before next run...")
    print("⏸️  "*40 + "\n")
    await asyncio.sleep(3)

    # Run without tools
    print("\n📍 PART 2: Running WITHOUT Memory Tools (Automatic Services)\n")
    without_tools_log = await run_travel_agent_without_tools()

    # Generate comparison
    print("\n\n" + "📊 "*40)
    print("COMPARISON SUMMARY")
    print("📊 "*40 + "\n")

    print("KEY DIFFERENCES:\n")
    print("1. MEMORY CONTROL:")
    print("   WITH Tools: LLM explicitly calls memory tools (create_memory, search_memory, etc.)")
    print("   WITHOUT Tools: Framework automatically extracts/retrieves memories via callbacks\n")

    print("2. USER EXPERIENCE:")
    print("   WITH Tools: Agent explicitly tells user when storing/updating/deleting memories")
    print("   WITHOUT Tools: Memory operations are implicit, agent just 'remembers'\n")

    print("3. FLEXIBILITY:")
    print("   WITH Tools: User can explicitly ask to 'remember this' or 'forget that'")
    print("   WITHOUT Tools: Memory extraction is automatic based on conversation content\n")

    print("4. USE CASES:")
    print("   WITH Tools: Best when users want explicit control over what's remembered")
    print("   WITHOUT Tools: Best for seamless, automatic personalization\n")

    print("5. IMPLEMENTATION:")
    print("   WITH Tools: Add memory tools to agent.tools list")
    print("   WITHOUT Tools: Configure memory_service + before/after callbacks\n")

    print("\n" + "✅ "*40)
    print("COMPARISON COMPLETE")
    print("✅ "*40 + "\n")


if __name__ == "__main__":
    asyncio.run(compare_approaches())

