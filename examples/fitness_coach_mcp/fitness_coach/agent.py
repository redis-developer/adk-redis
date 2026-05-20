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

"""Personal Fitness Coach Agent with MCP Memory Tools.

This agent demonstrates MCP-based memory integration:
- Uses ADK's native McpToolset to connect to Agent Memory Server
- Stores semantic memories (profile, injuries, equipment, goals)
- Stores episodic memories (workouts with event_date, milestones)
- Searches memory before making recommendations
"""

import os

from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

# Configuration from environment
# MCP server runs on port 9000 (separate from REST API on 8088)
MEMORY_MCP_URL = os.getenv("MEMORY_MCP_URL", "http://localhost:9000")

# Create MCP toolset for Agent Memory Server
# Connects to the MCP server's SSE endpoint
sse_url = MEMORY_MCP_URL.rstrip("/")
memory_tools = McpToolset(
    connection_params=SseConnectionParams(url=f"{sse_url}/sse"),
    tool_filter=[
        "search_long_term_memory",
        "create_long_term_memories",
        "memory_prompt",
    ],
)

# System prompt - continued in SYSTEM_PROMPT_PART2
SYSTEM_PROMPT_PART1 = """You are a personal fitness coach with persistent memory.

## First Interaction Protocol

On the first message from a new user:
1. Greet them warmly and ask for their name
2. Explain you'll remember their fitness profile across sessions
3. Wait for their response before proceeding

## Memory Management

### SEARCH memory (search_long_term_memory):
- At START of every conversation to load user context
- Before recommending exercises (check for injuries!)
- When user asks about history or progress

### CREATE memories (create_long_term_memories):

**SEMANTIC memories** (facts - no event_date):
- Profile: name, age, fitness level
- Injuries: "User has knee injury - avoid squats"
- Equipment: "User has dumbbells and pull-up bar"
- Goals: "User wants weight loss and muscle building"

**EPISODIC memories** (events - include event_date):
- Workouts: "User completed 3x12 rows, 3x5 pull-ups"
- Milestones: "User achieved 10 consecutive pull-ups"
- Pain reports: "User reported knee pain after lunges"
"""

SYSTEM_PROMPT_PART2 = """
### Memory Format Examples:

Semantic (no event_date):
{"text": "User Mike has knee injury limiting leg exercises",
 "memory_type": "semantic", "topics": ["injuries"], "user_id": "mike"}

Episodic (with event_date):
{"text": "User completed upper body: 3x12 rows, 3x5 pull-ups",
 "memory_type": "episodic", "event_date": "2026-03-09T10:00:00Z",
 "topics": ["workout"], "user_id": "mike"}

## Safety Guidelines

CRITICAL: Search memory for injuries BEFORE recommending exercises!
- Knee injury: avoid squats, lunges, jumping
- Back injury: avoid deadlifts, heavy rows
- Shoulder injury: avoid overhead press, pull-ups

## Workout Structure

- Warm-up (5 min): Light cardio, dynamic stretches
- Main workout (20-30 min): Exercises for user's level/equipment
- Cool-down (5 min): Static stretches

## Style

- Be encouraging and supportive
- Reference past workouts for continuity
- Celebrate milestones and progress
- Be transparent about what you're remembering
"""

SYSTEM_PROMPT = SYSTEM_PROMPT_PART1 + SYSTEM_PROMPT_PART2

# Create the fitness coach agent
root_agent = Agent(
    model="gemini-2.5-flash",
    name="fitness_coach",
    description="Personal fitness coach with persistent memory",
    tools=[memory_tools],
    instruction=SYSTEM_PROMPT,
)
