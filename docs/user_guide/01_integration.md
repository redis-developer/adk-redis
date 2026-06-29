# Quickstart

Get an ADK agent running with Redis-backed sessions and long-term memory in
three steps. For the concepts behind each feature, see the
[Concepts](../concepts/index.md) section.

> **See also:** [ADK + Redis on redis.io](https://redis.io/docs/latest/integrate/google-adk/) for additional coverage.

## 1. Start infrastructure

Provide Redis Agent Memory connection settings:

```bash
export REDIS_MEMORY_BACKEND="redis-agent-memory"
export REDIS_AGENT_MEMORY_API_BASE_URL="https://..."
export REDIS_AGENT_MEMORY_STORE_ID="..."
export REDIS_AGENT_MEMORY_API_KEY="..."
```

These are the same variable names used by the
[managed memory quickstart](how_to_guides/managed_memory_setup.md) and the
integration tests. For the open source self-hosted Agent Memory Server, use
`REDIS_MEMORY_BACKEND="opensource-agent-memory"`, point
`REDIS_AGENT_MEMORY_API_BASE_URL` at your server, and omit the API key and
store ID unless your deployment requires them.

## 2. Install dependencies

```bash
pip install google-adk "adk-redis[memory]"
```

## 3. Wire services into an agent

```python
import os

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.runners import Runner
from google.adk.tools import load_memory
from google.adk.tools import preload_memory
from adk_redis import (
    REDIS_AGENT_MEMORY_BACKEND,
    RedisSessionMemoryService,
    RedisSessionMemoryServiceConfig,
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
)

# REDIS_AGENT_MEMORY_BACKEND and OPENSOURCE_AGENT_MEMORY_BACKEND are typo-safe
# aliases for the "redis-agent-memory" and "opensource-agent-memory" strings.
backend = os.getenv("REDIS_MEMORY_BACKEND", REDIS_AGENT_MEMORY_BACKEND)

session_service = RedisSessionMemoryService(
    config=RedisSessionMemoryServiceConfig(
        backend=backend,
        api_base_url=os.environ["REDIS_AGENT_MEMORY_API_BASE_URL"],
        api_key=os.environ.get("REDIS_AGENT_MEMORY_API_KEY"),
        store_id=os.environ.get("REDIS_AGENT_MEMORY_STORE_ID"),
        default_namespace="my_app",
    )
)

memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        backend=backend,
        api_base_url=os.environ["REDIS_AGENT_MEMORY_API_BASE_URL"],
        api_key=os.environ.get("REDIS_AGENT_MEMORY_API_KEY"),
        store_id=os.environ.get("REDIS_AGENT_MEMORY_STORE_ID"),
        default_namespace="my_app",
    )
)


async def after_agent(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()


agent = Agent(
    name="memory_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant with long-term memory.",
    tools=[preload_memory, load_memory],
    after_agent_callback=after_agent,
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
2. Start a new session: "What do you remember about me?"

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
