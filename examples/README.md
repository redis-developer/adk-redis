# Examples

Runnable agents built with [Google ADK](https://github.com/google/adk-python)
and `adk-redis`. Each example ships with a README and `.env.example`.

## Memory and sessions

| Example | Backend default | Runner | What it exercises |
|---------|-----------------|--------|-------------------|
| [`managed_memory_quickstart`](managed_memory_quickstart/) | `redis-agent-memory` (managed) | `python main.py` | Minimal session + long-term memory services against managed Redis Agent Memory. No Docker. |
| [`simple_redis_memory`](simple_redis_memory/) | `opensource-agent-memory` | `python main.py` | Full two-tier memory with auto-summarization and extraction via Agent Memory Server. |
| [`travel_agent_memory_hybrid`](travel_agent_memory_hybrid/) | `opensource-agent-memory` | `python main.py` | Services + explicit memory tools + travel domain tools. |
| [`travel_agent_memory_tools`](travel_agent_memory_tools/) | `opensource-agent-memory` | `adk web .` | Memory tools only (no framework services). Switch backend via `REDIS_MEMORY_BACKEND`. |
| [`fitness_coach_mcp`](fitness_coach_mcp/) | `opensource-agent-memory` only | `adk web .` | MCP memory tools via Agent Memory Server SSE. Managed backend has no MCP endpoint. |

### Runner notes

- **`python main.py`** — Required when registering `RedisSessionMemoryService`
  and/or `RedisLongTermMemoryService` through `get_service_registry()`. ADK's
  `get_fast_api_app` reads those registrations; `adk web` does not.
- **`adk web .`** — Works when memory is wired as agent tools in `agent.py`
  (no custom session/memory services).

### Backend notes

- **`redis-agent-memory`** — Managed Redis Agent Memory (library default). Needs
  `REDIS_AGENT_MEMORY_API_BASE_URL`, `REDIS_AGENT_MEMORY_API_KEY`, and
  `REDIS_AGENT_MEMORY_STORE_ID`. No local Agent Memory Server.
- **`opensource-agent-memory`** — Self-hosted
  [Agent Memory Server](https://github.com/redis/agent-memory-server). Supports
  auto-summarization, extraction strategies, recency-boosted search, and MCP.

Set `REDIS_MEMORY_BACKEND` in examples that support both backends.

## Search

| Example | Runner | What it exercises |
|---------|--------|-------------------|
| [`redis_search_tools`](redis_search_tools/) | `adk web .` | Vector, text, and range search tools |
| [`redis_sql_search`](redis_sql_search/) | `adk web .` | `RedisSQLSearchTool` |
| [`redisvl_mcp_search`](redisvl_mcp_search/) | `adk web .` | RedisVL data via `rvl mcp` |

## Caching

| Example | Runner | What it exercises |
|---------|--------|-------------------|
| [`semantic_cache`](semantic_cache/) | `python main.py` | `RedisVLCacheProvider` semantic cache |
| [`langcache_cache`](langcache_cache/) | `python main.py` | Managed `LangCacheProvider` |
