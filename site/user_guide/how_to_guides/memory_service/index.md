# Memory Service

This guide shows how to wire `RedisMemoryService` into a Google ADK agent for persistent long-term memory.

## Prerequisites

- Redis Agent Memory Server running on `localhost:8000`
- `adk-redis` installed: `pip install adk-redis`

## Basic usage

```python
from google.adk.agents import Agent
from adk_redis import RedisMemoryService

# Create Redis-backed memory service
memory_service = RedisMemoryService(
    memory_server_url="http://localhost:8000",
    namespace="my-app",
)

# Use with your ADK agent
agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant with memory.",
)
```

## How memories flow

1. The agent converses with the user in a session
1. At session end, the memory service extracts key facts
1. Facts are stored in the Agent Memory Server as long-term memories
1. On future sessions, the agent retrieves relevant memories via semantic search

## Configuration options

| Option              | Default                 | Description                    |
| ------------------- | ----------------------- | ------------------------------ |
| `memory_server_url` | `http://localhost:8000` | Agent Memory Server URL        |
| `namespace`         | `default`               | Memory namespace for isolation |
