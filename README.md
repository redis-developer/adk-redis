<div align="center">
  <h1>
    <img src="https://raw.githubusercontent.com/redis/redis-vl-python/main/docs/_static/Redis_Logo_Red_RGB.svg" width="120" alt="Redis" style="vertical-align: middle; margin-right: 20px;">
    <span style="vertical-align: middle; margin: 0 10px;">×</span>
    <img src="https://raw.githubusercontent.com/google/adk-python/main/assets/agent-development-kit.png" width="120" alt="ADK" style="vertical-align: middle; margin-left: 20px;">
  </h1>
  <h1>Redis Integrations for Google Agent Development Kit</h1>
</div>

<div align="center">

[![PyPI version](https://badge.fury.io/py/adk-redis.svg)](https://badge.fury.io/py/adk-redis)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: pyink](https://img.shields.io/badge/code%20style-pyink-black)](https://github.com/google/pyink)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)

**[PyPI](https://pypi.org/project/adk-redis/)** • **[Documentation](https://redis.io/docs/latest/integrate/google-adk/)** • **[Examples](examples/)** • **[Agent Memory Server](https://github.com/redis/agent-memory-server)** • **[RedisVL](https://docs.redisvl.com)**

</div>

---

## What it does

`adk-redis` is the Redis layer for [Google ADK](https://github.com/google/adk-python) agents. It implements ADK's `BaseMemoryService`, `BaseSessionService`, and `BaseTool` interfaces against Redis, [RedisVL](https://docs.redisvl.com), and the [Redis Agent Memory Server](https://github.com/redis/agent-memory-server). It also ships MCP toolset helpers and semantic-cache providers.

| Surface | What you get | Backed by |
|---|---|---|
| **Sessions** (`RedisWorkingMemorySessionService`) | `BaseSessionService` with auto-summarization and context-window management | Agent Memory Server (REST) |
| **Long-term memory** (`RedisLongTermMemoryService`) | `BaseMemoryService` with semantic search and recency boosting | Agent Memory Server (REST) |
| **Memory tools** (`SearchMemoryTool`, `CreateMemoryTool`, ...) | LLM-controlled memory operations | Agent Memory Server (REST) |
| **RedisVL MCP** (native `McpToolset` against `rvl mcp`) | <ul><li>Tools exposed: `search-records`, `upsert-records` (gate writes with `--read-only`).</li><li>Search modes (one per server, chosen via YAML): `vector` KNN, `fulltext` BM25, or `hybrid` (LINEAR or RRF fusion).</li><li>Server-side query embedding via a configured RedisVL vectorizer; agents never load one locally.</li><li>Schema-aware tool descriptions: filter and return-field hints derived from the bound `IndexSchema`.</li><li>JSON filter language with tag, text, and numeric operators (`eq`, `in`, `between`, `gt`, `lt`, `ne`).</li><li>Transports: stdio, sse, streamable-http. Bearer auth on HTTP. Pagination via `limit` / `offset`.</li></ul> | `rvl mcp` server (`redisvl[mcp]`) |
| **Search tools with REST** (5 in-process tools) | Vector, hybrid, range, text, SQL search as `BaseTool` subclasses | RedisVL (Python) |
| **Semantic cache** (`RedisVLCacheProvider`, `LangCacheProvider`) | Skip repeat LLM calls and tool calls by semantic similarity | RedisVL `SemanticCache` or [Redis LangCache](https://redis.io/langcache) |

---

## Installation

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
pip install 'adk-redis[all,examples]'  # plus dotenv etc. for running examples

# For the RedisVL MCP server (used with ADK's native McpToolset):
pip install 'redisvl[mcp]>=0.18.2'
```

### Verify

```bash
python -c "from adk_redis import __version__; print(__version__)"
```

### Development install

```bash
git clone https://github.com/redis-developer/adk-redis.git
cd adk-redis
pip install uv
uv sync --all-extras
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Redis 8.4+ with the Redis Query Engine (Search). Local Docker:
  ```bash
  docker run -d --name redis -p 6379:6379 redis:8.4
  docker exec redis redis-cli ping   # -> PONG
  ```
- For session / memory services: a running [Agent Memory Server](https://github.com/redis/agent-memory-server) (default port 8088). Quick start:
  ```bash
  docker run -d --name agent-memory-server -p 8088:8088 \
    -e REDIS_URL=redis://host.docker.internal:6379 \
    -e GEMINI_API_KEY=YOUR_KEY \
    -e GENERATION_MODEL=gemini/gemini-2.5-flash \
    -e EMBEDDING_MODEL=gemini/text-embedding-004 \
    redislabs/agent-memory-server:0.13.2 \
    agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
  ```
  On Linux, `host.docker.internal` is not routable by default; use `--network=host` and `REDIS_URL=redis://127.0.0.1:6379`, or set `REDIS_URL` to the Docker-bridge gateway (typically `redis://172.17.0.1:6379`). AMS supports 100+ LLM and embedding providers via [LiteLLM](https://docs.litellm.ai/). See [Agent Memory Server setup](docs/user_guide/how_to_guides/memory_server_setup.md) for the full configuration matrix.

For Redis Cloud, Redis Enterprise, or troubleshooting, see [Redis setup](docs/user_guide/how_to_guides/redis_setup.md).

### Sessions + long-term memory

Two-tier memory: working memory (per session) and long-term memory (cross-session). Both implement ADK's service interfaces and slot into any `Runner`.

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
        api_base_url="http://localhost:8088",
        default_namespace="my_app",
        model_name="gpt-4o",
        context_window_max=8000,
    ),
)
memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        api_base_url="http://localhost:8088",
        default_namespace="my_app",
        extraction_strategy="discrete",
        recency_boost=True,
    ),
)

agent = Agent(
    model="gemini-2.5-flash",
    name="memory_agent",
    instruction="You are a helpful assistant with long-term memory.",
)

runner = Runner(
    app_name="my_app",
    agent=agent,
    session_service=session_service,
    memory_service=memory_service,
)
```

How it works: the session service stores conversation events in working memory and auto-summarizes when the token budget is hit; the memory service runs background extraction to long-term memory and surfaces a recency-boosted semantic search.

### Search over a Redis index (in-process)

```python
from google.adk import Agent
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis import RedisVectorQueryConfig, RedisVectorSearchTool

vectorizer = HFTextVectorizer(model="redis/langcache-embed-v2")
index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")

search_tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisVectorQueryConfig(num_results=5),
    return_fields=["name", "description", "price"],
    name="search_product_catalog",
    description="Find products by semantic similarity to the user's query.",
)

agent = Agent(
    model="gemini-2.5-flash",
    name="search_agent",
    instruction="Help users find products.",
    tools=[search_tool],
)
```

All five search tools accept custom `name` / `description` so the LLM sees a domain-specific tool rather than a generic search helper.

### Search over a Redis index (MCP)

Run `rvl mcp --config mcp_config.yaml` separately, then connect the agent with ADK's standard `McpToolset`:

```python
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

agent = Agent(
    model="gemini-2.5-flash",
    name="mcp_search_agent",
    instruction="Use the search-records tool to answer questions.",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="rvl",
                    args=[
                        "mcp",
                        "--config",
                        "/path/to/mcp_config.yaml",
                        "--read-only",
                    ],
                ),
                timeout=30,
            ),
            tool_filter=["search-records"],
        ),
    ],
)
```

For an already-running remote server, swap `StdioConnectionParams` for `StreamableHTTPConnectionParams(url="http://localhost:8765/mcp", headers={"Authorization": "Bearer ..."})`.

See [examples/redisvl_mcp_search/](examples/redisvl_mcp_search/) for a runnable demo (knowledge-base corpus, hybrid mode, paired with the in-process [examples/redis_search_tools/](examples/redis_search_tools/) example).

### Semantic cache

```python
from google.adk import Agent
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
        distance_threshold=0.1,
    ),
    vectorizer=HFTextVectorizer(model="redis/langcache-embed-v2"),
)
llm_cache = LLMResponseCache(provider=provider)
before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

agent = Agent(
    model="gemini-2.5-flash",
    name="cached_agent",
    before_model_callback=before_cb,
    after_model_callback=after_cb,
)
```

For a managed alternative that needs no local vectorizer, swap in `LangCacheProvider` / `LangCacheProviderConfig` from `adk_redis`.

---

## Search tools

Two parallel paths for RAG over a Redis index. Pick by deployment shape.

| Path | Use when |
|---|---|
| **In-process** | Single ADK process, fast onboarding, Python-side `FilterExpression` composition, per-tool customization. |
| **MCP** (ADK's `McpToolset` against `rvl mcp`) | One Redis index served to multiple agents (Python, JS, Claude Desktop). Server-side `--read-only` / bearer auth. Schema-aware tool descriptions. |

### In-process tools

| Tool | Best for | Notes |
|---|---|---|
| `RedisVectorSearchTool` | Semantic similarity | KNN vector search with metadata filters |
| `RedisHybridSearchTool` | Combined search | Vector + BM25; native `FT.HYBRID` on Redis 8.4+, aggregation fallback below |
| `RedisRangeSearchTool` | Threshold retrieval | Distance-bounded vector search. **No MCP equivalent.** |
| `RedisTextSearchTool` | Keyword search | BM25 full-text; no embeddings needed |
| `RedisSQLSearchTool` | SQL-style filters | `SELECT ... WHERE` with `:param` placeholders. Requires `adk-redis[sql]`. **No MCP equivalent.** |

All five accept any vectorizer supported by RedisVL (OpenAI, HuggingFace, Cohere, Mistral, Voyage AI, custom) and any `FilterExpression` from `redisvl.query.filter`.

### MCP

Use ADK's standard `McpToolset` against a running [RedisVL MCP server](https://docs.redisvl.com) (`rvl mcp`). The server is configured per index via YAML and exposes:

- `search-records`: `vector`, `fulltext`, or `hybrid` (chosen at server start). Tool description includes filter and return-field hints derived from the bound index schema.
- `upsert-records`: write path (suppress with `--read-only`).

Supports `stdio`, `sse`, and `streamable-http` transports; bearer auth on HTTP. Requires `redisvl[mcp]` and a `rvl mcp` server. See the [Quick Start MCP snippet](#search-over-a-redis-index-mcp) above for the wiring.

For the full decision matrix and runnable demo, see [docs/user_guide/how_to_guides/search_tools.md](docs/user_guide/how_to_guides/search_tools.md).

---

## Memory backends

Two ways to ingest, store, and retrieve memory with Agent Memory Server, both interoperable:

| Approach | What it is | Reach for it when |
|---|---|---|
| **ADK Services** (`RedisLongTermMemoryService`, `RedisWorkingMemorySessionService`) | The `BaseMemoryService` and `BaseSessionService` implementations. ADK calls AMS for you. | You want framework-managed sessions and automatic memory extraction. Most production cases. |
| **REST tools** (`MemoryPromptTool`, `SearchMemoryTool`, `CreateMemoryTool`, `UpdateMemoryTool`, `DeleteMemoryTool`, `GetMemoryTool`) | `BaseTool` subclasses that call AMS REST directly. The LLM decides when to invoke them. | You want the agent to control when memory is read or written. |

Both approaches use REST and operate on the same underlying memory. If you need MCP access to Agent Memory Server, use ADK's native `McpToolset` with `SseConnectionParams` pointed at the AMS `/sse` endpoint.

---

## Semantic cache

Two providers, both implementing `BaseCacheProvider`. Pair either with `LLMResponseCache` or `ToolCache` and wire via `create_llm_cache_callbacks` / `create_tool_cache_callbacks`.

| Provider | Hosted | Vectorizer | Best for |
|---|---|---|---|
| `RedisVLCacheProvider` | Self-hosted Redis | Required (any RedisVL vectorizer) | Full control, your data stays in your Redis |
| `LangCacheProvider` | Managed via [Redis LangCache](https://redis.io/langcache) | Server-side (none needed locally) | Zero-infra cache; no local Redis needed |

Both honor a configurable `distance_threshold` and per-entry `ttl`.

---

## Requirements

- Python 3.10, 3.11, 3.12, or 3.13
- Google ADK 1.0+ (tested through 2.0 GA)
- RedisVL 0.18.2+ when the `search`, `langcache`, or `sql` extra is installed
- Redis 8.4+ (or Redis Cloud with Search) when using search tools or the cache providers
- For session / memory services: a running [Agent Memory Server](https://github.com/redis/agent-memory-server)
- For `RedisSQLSearchTool`: `sql-redis` (installed by `adk-redis[sql]`)
- For the RedisVL MCP server: install `redisvl[mcp]>=0.18.2` and use the `rvl mcp` CLI; connect from ADK with `McpToolset`

---

## Examples

All examples run via `adk web` and ship with a README and `.env.example`.

| Example | Demonstrates |
|---|---|
| [`simple_redis_memory`](examples/simple_redis_memory/) | Two-tier memory + auto-summarization |
| [`travel_agent_memory_hybrid`](examples/travel_agent_memory_hybrid/) | Framework-managed memory: `RedisWorkingMemorySessionService` + `RedisLongTermMemoryService` in a custom FastAPI runner |
| [`travel_agent_memory_tools`](examples/travel_agent_memory_tools/) | LLM-controlled memory: REST `SearchMemoryTool` / `CreateMemoryTool` / etc. in a default ADK runner |
| [`fitness_coach_mcp`](examples/fitness_coach_mcp/) | AMS memory exposed over MCP via ADK's native `McpToolset` |
| [`redis_search_tools`](examples/redis_search_tools/) | In-process RAG with vector + text + range search tools |
| [`redis_sql_search`](examples/redis_sql_search/) | `RedisSQLSearchTool` answering catalog questions via parameterized SQL |
| [`redisvl_mcp_search`](examples/redisvl_mcp_search/) | Same knowledge base as `redis_search_tools/`, served via `rvl mcp` over MCP |
| [`semantic_cache`](examples/semantic_cache/) | Self-hosted semantic cache via `RedisVLCacheProvider` |
| [`langcache_cache`](examples/langcache_cache/) | Managed semantic cache via `LangCacheProvider` |

The two travel-agent examples use the same Agent Memory Server backend; the difference is whether the agent talks to AMS through framework services (`hybrid`) or LLM-driven tool calls (`tools`).

---

## Development

This project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), matching the [ADK-Python core](https://github.com/google/adk-python) project conventions.

### Setup

```bash
git clone https://github.com/redis-developer/adk-redis.git
cd adk-redis
make dev               # install with all extras + dev deps
make check             # format-check + lint + type-check + test
```

### Targets

```bash
make format            # apply pyink + isort
make lint              # ruff check
make type-check        # mypy
make test              # all tests (unit + integration)
make test-unit         # unit tests only (no Redis required)
make test-integration  # integration suite (needs Redis 8.4+ at REDIS_URL)
make redis-up          # start a redis:8.4 container on :6399 for integration
make redis-down        # stop and remove that container
make test-cov          # coverage report
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for testing, style, and PR conventions.

---

## Contributing

Open an [issue](https://github.com/redis-developer/adk-redis/issues) for bugs and feature requests, or submit a PR following [CONTRIBUTING.md](CONTRIBUTING.md). Documentation and example contributions are equally welcome.

---

## License

Apache 2.0. See [LICENSE](LICENSE).

---

## Helpful links

- [PyPI](https://pypi.org/project/adk-redis/): install with `pip install adk-redis`
- [Redis setup](docs/user_guide/how_to_guides/redis_setup.md): local, Docker, and Redis Cloud
- [Agent Memory Server setup](docs/user_guide/how_to_guides/memory_server_setup.md): full AMS configuration
- [Integration walkthrough](docs/user_guide/01_integration.md): end-to-end wiring
- [Search tools guide](docs/user_guide/how_to_guides/search_tools.md): in-process vs MCP, decision matrix
- [Google ADK](https://github.com/google/adk-python): agent framework
- [Agent Memory Server](https://github.com/redis/agent-memory-server): memory backend
- [RedisVL](https://docs.redisvl.com/): Redis Vector Library
- [Redis LangCache](https://redis.io/langcache): managed semantic cache
