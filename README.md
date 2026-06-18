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

**[PyPI](https://pypi.org/project/adk-redis/)** • **[Documentation](https://redis-developer.github.io/adk-redis/)** • **[Examples](examples/)** • **[Agent Memory Server](https://github.com/redis/agent-memory-server)** • **[RedisVL](https://docs.redisvl.com)**

</div>

---

`adk-redis` is the Redis layer for [Google ADK](https://github.com/google/adk-python) agents. It implements ADK's `BaseMemoryService`, `BaseSessionService`, and `BaseTool` interfaces against Redis, [RedisVL](https://docs.redisvl.com), Redis Agent Memory, and the [Redis Agent Memory Server](https://github.com/redis/agent-memory-server). It also ships MCP toolset helpers and semantic-cache providers.

| Surface | What you get | Backed by |
|---|---|---|
| **Sessions** | `BaseSessionService` with durable conversation state | Redis Agent Memory or Agent Memory Server |
| **Long-term memory** | `BaseMemoryService` with semantic search | Redis Agent Memory or Agent Memory Server |
| **Memory tools** | LLM-controlled memory CRUD operations | Redis Agent Memory or Agent Memory Server |
| **Search tools** | Vector, hybrid, range, text, and SQL search as `BaseTool` subclasses | RedisVL |
| **MCP search** | `search-records` / `upsert-records` via ADK's native `McpToolset` | `rvl mcp` server |
| **Semantic cache** | Skip repeat LLM calls by semantic similarity | RedisVL or [Redis LangCache](https://redis.io/langcache) |

→ *[Full documentation](https://redis-developer.github.io/adk-redis/)*

---

## Installation

```bash
pip install adk-redis
```

Optional extras:

```bash
pip install 'adk-redis[memory]'      # sessions + long-term memory services
pip install 'adk-redis[search]'      # RedisVL-backed search tools
pip install 'adk-redis[sql]'         # RedisSQLSearchTool
pip install 'adk-redis[langcache]'   # managed semantic cache provider
pip install 'adk-redis[all]'         # everything above
```

Memory backends are selected with `backend`:

| Backend | Use when | Client |
|---|---|---|
| `redis-agent-memory` | You want Redis Agent Memory managed by Redis or the Redis Agent Memory data plane | `redis-agent-memory` |
| `opensource-agent-memory` | You want the open source self-hosted Agent Memory Server | `agent-memory-client` |

---

## Quick start

**Prerequisites:** Python 3.10+, Redis 8.4+, and one memory backend. See the [Quickstart](https://redis-developer.github.io/adk-redis/user_guide/01_integration/) for full setup steps.

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
        api_base_url="http://localhost:8088",
        api_key="...",
        store_id="...",
        default_namespace="my_app",
    ),
)
memory_service = RedisLongTermMemoryService(
    config=RedisLongTermMemoryServiceConfig(
        backend="redis-agent-memory",
        api_base_url="http://localhost:8088",
        api_key="...",
        store_id="...",
        default_namespace="my_app",
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

For the open source self-hosted Agent Memory Server, set
`backend="opensource-agent-memory"` and omit `api_key` and `store_id` unless your
server requires them.

→ *More examples: [search tools](https://redis-developer.github.io/adk-redis/user_guide/how_to_guides/search_tools/), [MCP search](https://redis-developer.github.io/adk-redis/concepts/search/), [semantic caching](https://redis-developer.github.io/adk-redis/user_guide/how_to_guides/semantic_cache/)*

---

## Examples

Each example ships with a README and `.env.example`. Memory and session
examples that register services through `get_service_registry()` run via
`python main.py`; tools-only and search examples run via `adk web`. See each
example's README and the [Examples index](https://redis-developer.github.io/adk-redis/examples/) for the runner and backend each uses.

| Category | Examples |
|---|---|
| **Memory and sessions** | [`managed_memory_quickstart`](examples/managed_memory_quickstart/) · [`simple_redis_memory`](examples/simple_redis_memory/) · [`travel_agent_memory_hybrid`](examples/travel_agent_memory_hybrid/) · [`travel_agent_memory_tools`](examples/travel_agent_memory_tools/) · [`fitness_coach_mcp`](examples/fitness_coach_mcp/) |
| **Search** | [`redis_search_tools`](examples/redis_search_tools/) · [`redis_sql_search`](examples/redis_sql_search/) · [`redisvl_mcp_search`](examples/redisvl_mcp_search/) |
| **Caching** | [`semantic_cache`](examples/semantic_cache/) · [`langcache_cache`](examples/langcache_cache/) |

---

## Development

```bash
git clone https://github.com/redis-developer/adk-redis.git
cd adk-redis
make dev               # install with all extras + dev deps
make check             # format, lint, type-check, and test
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

---

## Contributing

Open an [issue](https://github.com/redis-developer/adk-redis/issues) or submit a PR following [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0. See [LICENSE](LICENSE).

---

## Links

- **[Documentation](https://redis-developer.github.io/adk-redis/)**: concepts, how-to guides, API reference
- [Google ADK](https://github.com/google/adk-python) · [Agent Memory Server](https://github.com/redis/agent-memory-server) · [RedisVL](https://docs.redisvl.com) · [Redis LangCache](https://redis.io/langcache)
- [ADK + Redis on redis.io](https://redis.io/docs/latest/integrate/google-adk/)
