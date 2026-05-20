# Personal Fitness Coach with MCP Memory

A personal fitness coaching agent demonstrating **MCP-based memory integration** with Redis Agent Memory Server.

## Overview

This example showcases MCP (Model Context Protocol) tools for memory operations:
- **MCP Tools** - `search_long_term_memory`, `create_long_term_memories`, `memory_prompt`
- **Semantic Memory** - User profile, injuries, equipment, goals
- **Episodic Memory** - Completed workouts (with `event_date`), milestones, pain reports
- **Cross-session Personalization** - Coach remembers user across conversations

**Key Difference from other examples:**

| Example | Memory Approach | How to Run |
|---------|-----------------|------------|
| `simple_redis_memory` | ADK services (`BaseMemoryService`) | `adk web .` |
| `travel_agent_memory_hybrid` | REST services + tools | `python main.py` |
| `travel_agent_memory_tools` | REST tools only | `adk web .` |
| **`fitness_coach_mcp`** | **MCP tools via SSE** | `adk web .` |

## Quick Start

### 1. Start Services

```bash
cd examples/fitness_coach_mcp
docker compose up -d
```

**What's running:**
- **Redis 8.4** on port 6379
- **Agent Memory Server** on port 8088 (with MCP/SSE endpoint)

### 2. Setup Environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY and GEMINI_API_KEY
```

### 3. Run the Agent

```bash
cd examples/fitness_coach_mcp
uv run adk web .
```

Open **http://localhost:8000** in your browser.

---

## How MCP Memory Works

This example uses ADK's native `McpToolset` to connect to the Agent Memory Server's MCP endpoint:

```python
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

memory_tools = McpToolset(
    connection_params=SseConnectionParams(url="http://localhost:8088/sse"),
    tool_filter=[
        "search_long_term_memory",
        "create_long_term_memories",
        "memory_prompt",
    ],
)

agent = Agent(
    model="gemini-2.5-flash",
    name="fitness_coach",
    tools=[memory_tools],
)
```

**MCP vs REST Tools:**

| Aspect | MCP Tools | REST Tools |
|--------|-----------|------------|
| Protocol | SSE (Server-Sent Events) | HTTP REST |
| Connection | Persistent stream | Request/response |
| Implementation | `McpToolset` | Custom `FunctionTool` |
| Tool Discovery | Automatic from server | Manual definition |

---

## Memory Types

### Semantic Memory (Facts & Preferences)

Stored without `event_date` - represents persistent knowledge:

```json
{
  "text": "User Mike has a knee injury that limits leg exercises",
  "memory_type": "semantic",
  "topics": ["injuries", "limitations"],
  "entities": ["knee", "injury"],
  "user_id": "mike"
}
```

**Examples:**
- User profile (name, age, fitness level)
- Injuries and limitations
- Available equipment
- Fitness goals
- Workout preferences

### Episodic Memory (Events with Time)

Stored with `event_date` - represents specific events:

```json
{
  "text": "User completed upper body workout: 3x12 rows, 3x5 pull-ups",
  "memory_type": "episodic",
  "event_date": "2026-03-09T10:00:00Z",
  "topics": ["workout", "upper-body"],
  "entities": ["dumbbell rows", "pull-ups"],
  "user_id": "mike"
}
```

**Examples:**
- Completed workouts
- Personal records / milestones
- Pain reports
- Progress notes

---

## Testing Scenarios

### Scenario 1: Initial Profile Setup

```
USER: Hi, I want to get in shape

COACH: Hello! I'm your personal fitness coach. To provide personalized 
       workouts and track your progress, may I ask your name?

USER: I'm Mike. I have a knee injury and want to build upper body strength.
      I have dumbbells and a pull-up bar at home.

COACH: Great to meet you, Mike! I've noted:
       - Knee injury (I'll avoid exercises that stress your knee)
       - Goal: Build upper body strength
       - Equipment: Dumbbells and pull-up bar at home
       
       Let's design a safe upper body program for you!
```

### Scenario 2: Log a Workout

```
USER: I just completed 3x12 dumbbell rows and 3x5 pull-ups

COACH: Excellent work, Mike! I've logged your workout:
       - 3x12 dumbbell rows
       - 3x5 pull-ups
       
       That's solid progress on your upper body strength goal!
       How did it feel? Any discomfort?
```

### Scenario 3: Memory Recall (New Session)

```
USER: What do you know about my fitness goals and recent workouts?

COACH: Let me check my memory... 
       
       Mike, here's what I remember about you:
       - Goal: Build upper body strength
       - Limitation: Knee injury (avoiding leg exercises)
       - Equipment: Dumbbells and pull-up bar at home
       
       Recent workouts:
       - March 9: Upper body - 3x12 rows, 3x5 pull-ups
       
       Ready for your next workout?
```

---

## Architecture

### Memory Flow

```
User Message
    ↓
[search_long_term_memory] ← Search for user context, injuries
    ↓
[Agent Processing] ← Generate workout recommendations
    ↓
Agent Response
    ↓
[create_long_term_memories] ← Store new info (profile, workouts)
```

### MCP Connection

```
ADK Agent
    ↓
McpToolset (SSE connection)
    ↓
Agent Memory Server (/sse endpoint)
    ↓
Redis (vector storage)
```

### File Structure

```
examples/fitness_coach_mcp/
├── README.md                 # This file
├── docker-compose.yml        # Redis + Agent Memory Server
├── .env.example              # Environment template
└── fitness_coach/            # Agent package
    ├── __init__.py           # Exports root_agent
    └── agent.py              # Agent with MCP tools
```

---

## Troubleshooting

### Agent Memory Server not running

```
Error: Connection refused to http://localhost:8088
```

**Solution:** Start services with Docker Compose:
```bash
cd examples/fitness_coach_mcp
docker compose up -d
```

### MCP connection fails

```
Error: Failed to connect to SSE endpoint
```

**Solution:** Verify Agent Memory Server is running and accessible:
```bash
curl http://localhost:8088/health
```

### Module not found

```
ModuleNotFoundError: No module named 'adk_redis'
```

**Solution:** Use `uv run` to run commands:
```bash
uv run adk web .
```

---

## Learn More

- [ADK-Redis Documentation](../../README.md)
- [Integration Guide](../../docs/integration-guide.md)
- [Agent Memory Server Docs](https://redis.github.io/agent-memory-server/)
- [Memory Types](https://redis.github.io/agent-memory-server/long-term-memory/)

---

## License

Copyright 2025 Google LLC and Redis, Inc.

Licensed under the Apache License, Version 2.0. See [LICENSE](../../LICENSE) for details.
