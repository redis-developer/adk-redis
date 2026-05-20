# Quickstart

Get an ADK agent running with Redis-backed sessions and long-term memory in
three steps. For the concepts behind each feature, see the
[Concepts](../concepts/index.md) section.

> **See also:** [ADK + Redis on redis.io](https://redis.io/docs/latest/integrate/google-adk/) for additional coverage.

## 1. Start infrastructure

Follow the [Redis setup](how_to_guides/redis_setup.md) and
[Agent Memory Server setup](how_to_guides/memory_server_setup.md) how-to guides,
or use this minimal start:

```bash
# Redis 8.4
docker run -d --name redis -p 6379:6379 redis:8.4-alpine

# Agent Memory Server (dev mode)
docker run -d --name agent-memory-server \
  -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  -e DISABLE_AUTH=true \
  redislabs/agent-memory-server:0.13.2 \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio

# Verify
curl http://localhost:8000/v1/health
```

!!! note
    On Linux, replace `host.docker.internal` with `172.17.0.1` or use
    `--network host`.

## 2. Install dependencies

```bash
pip install google-adk "adk-redis[memory]"
```

## 3. Wire services into an agent

```python
from google.adk import Agent
from google.adk.runners import Runner
from adk_redis import (
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
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
    )
)

agent = Agent(
    name="memory_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant with long-term memory.",
)

runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

Launch the agent with the ADK runtime
([`adk web`](https://google.github.io/adk-docs/runtime/)):

```bash
adk web my_app
```

**Try it out:**

1. "Hi, I'm Alice. I love pizza and Python."
2. Wait 5 seconds for background memory extraction.
3. Start a new session: "What do you remember about me?"

## What next?

| Goal | Page |
|------|------|
| Understand sessions, memory, search, and caching | [Concepts](../concepts/index.md) |
| Configure session or memory services in detail | [Session service how-to](how_to_guides/session_service.md), [Memory service how-to](how_to_guides/memory_service.md) |
| Give the LLM explicit memory tools | [Sessions + Memory MCP + Tools](../concepts/memory.md) |
| Add vector or hybrid search | [Search tools how-to](how_to_guides/search_tools.md) |
| Reduce LLM cost with semantic caching | [Semantic Caching](../concepts/caching.md) |
| See a full working example | [Examples](../examples/index.md) |
| Run or deploy your agent | [ADK runtime](https://google.github.io/adk-docs/runtime/) |
