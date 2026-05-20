# Memory Service

This guide shows how to wire `RedisLongTermMemoryService` into a Google ADK
agent for persistent long-term memory backed by the
[Agent Memory Server](memory_server_setup.md).

For the concepts behind long-term memory, see
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
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

session_service = RedisWorkingMemorySessionService(
    config=RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://localhost:8000",
        default_namespace="my_app",
    )
)

memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        api_base_url="http://localhost:8000",
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

## How memories flow

1. The agent converses with the user in a session.
2. The Agent Memory Server extracts key facts in the background.
3. Facts are stored as long-term memories with vector embeddings.
4. On future sessions, the runner calls `search_memory()` and injects
   relevant memories into the prompt automatically.

## Configuration options

| Option | Default | Description |
|--------|---------|-------------|
| `api_base_url` | `http://localhost:8000` | Agent Memory Server URL |
| `default_namespace` | `None` | Namespace for memory isolation |
| `search_top_k` | `10` | Max memories per search |
| `distance_threshold` | `None` | Max distance for results (0.0-1.0) |
| `recency_boost` | `True` | Enable recency-aware ranking |
| `semantic_weight` | `0.8` | Weight for semantic similarity |
| `recency_weight` | `0.2` | Weight for recency score |
| `extraction_strategy` | `discrete` | `discrete`, `summary`, `preferences`, `custom` |
| `timeout` | `30.0` | HTTP request timeout |
