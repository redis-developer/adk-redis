# Session Service

This guide shows how to wire `RedisWorkingMemorySessionService` into a Google
ADK agent for durable session state backed by Redis Agent Memory session
events or self-hosted Agent Memory Server working memory.

For the concepts behind sessions and working memory, see
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

agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant.",
)

runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
)

# Create a session
session = await session_service.create_session(
    app_name="my_app",
    user_id="alice",
)

# Events appended to the session persist in the configured backend
```

For self-hosted Agent Memory Server, use `backend="opensource-agent-memory"` and
omit `api_key` and `store_id` unless your deployment requires them.

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| `backend` | `redis-agent-memory` | `redis-agent-memory` or `opensource-agent-memory` |
| `api_base_url` | `http://localhost:8000` | Memory backend URL |
| `api_key` | `None` | Redis Agent Memory API key |
| `store_id` | `None` | Redis Agent Memory store ID |
| `default_namespace` | `None` | Namespace for session isolation |
| `timeout` | `30.0` | HTTP request timeout |
