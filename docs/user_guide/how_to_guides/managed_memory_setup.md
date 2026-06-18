# Managed Redis Agent Memory Setup

This guide covers the **managed** `redis-agent-memory` backend, which is the
library default. For the self-hosted alternative, see
[Agent Memory Server setup](memory_server_setup.md).

The managed backend is a hosted Redis Agent Memory data plane: there is no
local Agent Memory Server, worker, or Docker setup to run. You connect to it
with an API base URL, an API key, and a store ID.

## Credentials

The managed backend requires three values from your Redis Agent Memory
deployment:

| Value | Config field | Environment variable |
|-------|--------------|----------------------|
| API base URL | `api_base_url` | `REDIS_AGENT_MEMORY_API_BASE_URL` |
| API key | `api_key` | `REDIS_AGENT_MEMORY_API_KEY` |
| Store ID | `store_id` | `REDIS_AGENT_MEMORY_STORE_ID` |

These are the same variable names used by the
[managed memory quickstart example](https://github.com/redis-developer/adk-redis/tree/main/examples/managed_memory_quickstart)
and the integration tests.

```bash
export REDIS_MEMORY_BACKEND="redis-agent-memory"
export REDIS_AGENT_MEMORY_API_BASE_URL="https://..."
export REDIS_AGENT_MEMORY_API_KEY="..."
export REDIS_AGENT_MEMORY_STORE_ID="..."
```

## Wiring the services

```python
import os

from adk_redis import (
    REDIS_AGENT_MEMORY_BACKEND,
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

session_service = RedisWorkingMemorySessionService(
    config=RedisWorkingMemorySessionServiceConfig(
        backend=REDIS_AGENT_MEMORY_BACKEND,
        api_base_url=os.environ["REDIS_AGENT_MEMORY_API_BASE_URL"],
        api_key=os.environ["REDIS_AGENT_MEMORY_API_KEY"],
        store_id=os.environ["REDIS_AGENT_MEMORY_STORE_ID"],
        default_namespace="my_app",
    )
)

memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        backend=REDIS_AGENT_MEMORY_BACKEND,
        api_base_url=os.environ["REDIS_AGENT_MEMORY_API_BASE_URL"],
        api_key=os.environ["REDIS_AGENT_MEMORY_API_KEY"],
        store_id=os.environ["REDIS_AGENT_MEMORY_STORE_ID"],
        default_namespace="my_app",
    )
)
```

`REDIS_AGENT_MEMORY_BACKEND` is a typo-safe alias for the
`"redis-agent-memory"` string. Either form works.

## Identifier constraints

The managed API accepts only alphanumeric characters and hyphens
(`[A-Za-z0-9-]`) in identifier fields such as namespace, session ID, and actor
ID, and caps session IDs at 64 characters. `adk-redis` adapts ADK identifiers
to fit:

- Namespaces and authors are sanitized: unsupported characters (including `_`
  and `:`) are replaced with hyphens. For example, `my_app` becomes `my-app`.
- ADK session IDs that exceed the limit or contain unsupported characters are
  hashed to a stable hex value that fits the 64-character cap.

This adaptation is automatic. You do not need to pre-sanitize identifiers, but
be aware that two raw namespaces that differ only by an unsupported character
(for example `my_app` and `my-app`) collapse to the same managed namespace.

## Differences from the self-hosted backend

The managed backend intentionally omits features that depend on a self-hosted
Agent Memory Server:

- No auto-summarization, extraction strategies, or recency-boosted search.
- No MCP endpoint. MCP memory tools require the
  [Agent Memory Server](memory_server_setup.md).

For a runnable minimal agent on the managed backend, see the
[managed memory quickstart example](https://github.com/redis-developer/adk-redis/tree/main/examples/managed_memory_quickstart).

## Next steps

- [Session service](session_service.md) and [Memory service](memory_service.md)
  for full configuration options.
- [Agent Memory Server setup](memory_server_setup.md) for the self-hosted
  backend with summarization, extraction, and MCP.
