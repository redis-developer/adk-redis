# Memory

`RedisMemoryService` connects ADK agents to the Redis Agent Memory Server, providing two-tier memory that persists across sessions.

## Two-tier model

| Tier                 | Scope           | Storage            | Search                    |
| -------------------- | --------------- | ------------------ | ------------------------- |
| **Working memory**   | Current session | Redis JSON         | None (use session state)  |
| **Long-term memory** | All sessions    | Redis vector index | Semantic, keyword, hybrid |

## How it works

1. During a conversation, the agent accumulates facts and preferences
1. When the session ends (or on explicit flush), memories are extracted and stored in long-term memory
1. On future sessions, the agent searches long-term memory to recall relevant context

## Configuration

`RedisMemoryService` connects to a running Agent Memory Server instance:

```python
from adk_redis import RedisMemoryService

memory = RedisMemoryService(
    memory_server_url="http://localhost:8000",
    namespace="my-app",
)
```

## Relationship to Agent Memory Server

`RedisMemoryService` is a thin client that proxies to the Agent Memory Server REST API. It does not implement memory logic itself. The server handles extraction, deduplication, and search.
