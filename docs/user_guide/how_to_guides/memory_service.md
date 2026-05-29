# Memory Service

This guide shows how to wire `RedisLongTermMemoryService` into a Google ADK
agent for persistent long-term memory backed by Redis Agent Memory or the
self-hosted Agent Memory Server.

For the concepts behind long-term memory, see
[Sessions + Memory Services](../../concepts/sessions.md).

## Prerequisites

- Redis Agent Memory endpoint, store ID, and API key, or a self-hosted Agent
  Memory Server endpoint.
- `adk-redis` with the memory extra: `pip install "adk-redis[memory]"`.

## Basic usage

```python
from google.adk import Agent
from google.adk.runners import Runner
from adk_redis import (
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

session_service = RedisWorkingMemorySessionService(
    config=RedisWorkingMemorySessionServiceConfig(
        backend="redis-agent-memory",
        api_base_url="http://localhost:8000",
        api_key="...",
        store_id="...",
        default_namespace="my_app",
    )
)

memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        backend="redis-agent-memory",
        api_base_url="http://localhost:8000",
        api_key="...",
        store_id="...",
        default_namespace="my_app",
        recency_boost=True,
    )
)

agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant with memory.",
)

runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

For self-hosted Agent Memory Server, use `backend="opensource-agent-memory"` and
omit `api_key` and `store_id` unless your deployment requires them.

## How memories flow

1. The agent converses with the user in a session.
2. `add_session_to_memory()` stores event text as long-term `message` memory.
3. Use `add_memory()` or memory tools to write durable facts and preferences.
4. On future sessions, the runner calls `search_memory()` and injects
   relevant memories into the prompt automatically.

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| `backend` | `redis-agent-memory` | `redis-agent-memory` or `opensource-agent-memory` |
| `api_base_url` | `http://localhost:8000` | Memory backend URL |
| `api_key` | `None` | Redis Agent Memory API key |
| `store_id` | `None` | Redis Agent Memory store ID |
| `default_namespace` | `None` | Namespace for memory isolation |
| `search_top_k` | `10` | Max memories per search |
| `similarity_threshold` | `None` | Min similarity for results (0.0-1.0) |
| `store_events_as_messages` | `True` | Store ADK events as `message` memories |
| `timeout` | `30.0` | HTTP request timeout |
