# Session Service

This guide shows how to wire `RedisWorkingMemorySessionService` into a Google
ADK agent for durable, auto-summarizing session state backed by the
[Agent Memory Server](memory_server_setup.md).

For the concepts behind sessions and working memory, see
[Sessions + Memory Services](../../concepts/sessions.md).

## Prerequisites

- Agent Memory Server running on `localhost:8000`
  (see [Memory server setup](memory_server_setup.md)).
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
        api_base_url="http://localhost:8000",
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

# The session is persisted in Agent Memory Server and survives restarts
```

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| `api_base_url` | `http://localhost:8000` | Agent Memory Server URL |
| `default_namespace` | `None` | Namespace for session isolation |
| `model_name` | `None` | LLM model for summarization |
| `context_window_max` | `None` | Max tokens before auto-summarization |
| `extraction_strategy` | `discrete` | `discrete`, `summary`, `preferences`, `custom` |
| `session_ttl_seconds` | `None` | Session expiration time |
| `timeout` | `30.0` | HTTP request timeout |
