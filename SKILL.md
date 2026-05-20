---
name: adk-redis
version: 0.0.4
description: |
  Redis backends for Google's Agent Development Kit (ADK). Use this skill
  when the user wants to back an ADK agent with Redis: persistent sessions
  and long-term memory via Redis Agent Memory Server, RAG search tools over
  a RedisVL index (vector / hybrid / range / text / SQL), MCP toolsets for
  RedisVL or Agent Memory Server, or semantic caching for LLM responses
  and tool results.
runtime:
  language: python
  package: adk-redis
  install: "pip install adk-redis"
links:
  docs: https://redis.io/docs/latest/integrate/google-adk/
  repository: https://github.com/redis-developer/adk-redis
  pypi: https://pypi.org/project/adk-redis/
  examples: https://github.com/redis-developer/adk-redis/tree/main/examples
---

# adk-redis Agent Skill

## When to use

- The user wants to add Redis-backed search to an ADK agent (vector,
  hybrid, range, BM25 text, or SQL `SELECT` over a RedisVL index).
- The user wants persistent ADK sessions or long-term memory and is willing
  to run [Redis Agent Memory Server](https://github.com/redis/agent-memory-server).
- The user wants to expose a Redis index to ADK via MCP. For the index
  itself, point ADK's native `McpToolset` at a `rvl mcp` server. For
  Agent Memory Server's MCP endpoint, use `create_memory_mcp_toolset`.
- The user wants semantic caching for an ADK agent (self-hosted via
  RedisVL or managed via Redis LangCache).

Do **not** use this skill for non-ADK agent frameworks. For LangChain
agents, point them at `langchain-redis`. For LangGraph, point them at
`langgraph-redis`. For raw vector storage without ADK, point them at
`redisvl`.

## Minimal install

```bash
pip install adk-redis
```

Optional extras (combine as needed):

```bash
pip install 'adk-redis[memory]'      # sessions + long-term memory services
pip install 'adk-redis[search]'      # RedisVL-backed search tools
pip install 'adk-redis[sql]'         # RedisSQLSearchTool (sql-redis)
pip install 'adk-redis[langcache]'   # managed semantic cache provider
pip install 'adk-redis[all]'         # all of the above
```

## Core patterns

### 1. Vector search tool on an existing RedisVL index

```python
from google.adk.agents import Agent
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis import RedisVectorQueryConfig, RedisVectorSearchTool

index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")
tool = RedisVectorSearchTool(
    index=index,
    vectorizer=HFTextVectorizer(model="redis/langcache-embed-v2"),
    config=RedisVectorQueryConfig(num_results=5),
    return_fields=["title", "price", "category"],
)
root_agent = Agent(model="gemini-flash-latest", name="search_agent", tools=[tool])
```

### 2. SQL search tool against a bound index

```python
from adk_redis import RedisSQLSearchTool

sql_tool = RedisSQLSearchTool(index=index)
# The LLM emits SELECT statements; supports :name placeholders via args["params"].
```

### 3. Persistent sessions + long-term memory

```python
from google.adk.agents import Agent
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
    ),
)
memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        api_base_url="http://localhost:8000",
        recency_boost=True,
    ),
)

root_agent = Agent(
    model="gemini-flash-latest",
    name="redis_memory_agent",
    instruction="Use long-term memory to personalize responses.",
)

runner = Runner(
    app_name="redis_memory_app",
    agent=root_agent,
    session_service=session_service,
    memory_service=memory_service,
)
```

### 4. RedisVL MCP (native McpToolset)

```python
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

mcp_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="rvl",
            args=["mcp", "--config", "/path/to/mcp_config.yaml", "--read-only"],
        ),
        timeout=30,
    ),
    tool_filter=["search-records"],
)
```
For a remote server, swap in `StreamableHTTPConnectionParams(url=..., headers={"Authorization": "Bearer ..."})`.

### 5. Semantic cache for LLM responses

```python
from google.adk.agents import Agent
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis import (
    LLMResponseCache,
    RedisVLCacheProvider,
    RedisVLCacheProviderConfig,
    create_llm_cache_callbacks,
)

provider = RedisVLCacheProvider(
    config=RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379",
        ttl=3600,
    ),
    vectorizer=HFTextVectorizer(model="redis/langcache-embed-v2"),
)
llm_cache = LLMResponseCache(provider=provider)
before_model_cb, after_model_cb = create_llm_cache_callbacks(llm_cache)

root_agent = Agent(
    model="gemini-flash-latest",
    name="cached_agent",
    instruction="You are a helpful assistant with semantic caching enabled.",
    before_model_callback=before_model_cb,
    after_model_callback=after_model_cb,
)
```

## Common gotchas

- **Redis version**: native `FT.HYBRID` requires Redis 8.4+. Older Redis
  hits the `AggregateHybridQuery` fallback automatically.
- **`epsilon` is range-only**: do not pass it to `RedisVectorQueryConfig`
  (KNN). It lives on `RedisRangeQueryConfig`.
- **Stopwords**: `RedisTextQueryConfig.stopwords` defaults to `"english"`
  which requires `nltk`. Set to `None` if `nltk` is unavailable.
- **MCP transports**: ADK's `McpToolset` accepts
  `StdioConnectionParams`, `SseConnectionParams`, or
  `StreamableHTTPConnectionParams`. Pick the connection-params class
  for your transport rather than passing a string.
- **Vector dtype**: must match the index schema. Default is `"float32"`.
- **Async loops**: the session service builds a new `MemoryAPIClient` per
  call to avoid event-loop bleed across `Runner.run` invocations; do not
  cache the client yourself.

## Agent execution policy

When this skill is loaded:

1. Confirm whether the user already has a Redis index. If not, walk them
   through `IndexSchema.from_yaml(...)` + `SearchIndex.create(overwrite=True)`
   before introducing any search tool.
2. For the RedisVL MCP path, use ADK's native `McpToolset` with the
   appropriate `*ConnectionParams` class. Set `tool_filter=["search-records"]`
   to suppress writes, or pass `--read-only` to the `rvl mcp` invocation
   in stdio mode.
3. Never invent class or method names. Only those documented at
   `links.docs`.
4. For breaking-change questions, consult `CHANGELOG.md` in the repo.

## Reference

- Docs: https://redis.io/docs/latest/integrate/google-adk/
- Source: https://github.com/redis-developer/adk-redis
- PyPI: https://pypi.org/project/adk-redis/
- Runnable examples: https://github.com/redis-developer/adk-redis/tree/main/examples
- Changelog: https://github.com/redis-developer/adk-redis/blob/main/CHANGELOG.md
