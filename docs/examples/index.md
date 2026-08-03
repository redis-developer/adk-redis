---
description: Worked agents built with adk-redis and the Google ADK.
---

# Examples

Runnable agents built with the Google ADK and Redis. Each links to its source
directory and explains what it demonstrates.

## Memory and Sessions

Each memory example targets a specific backend. The examples that exercise
auto-summarization, extraction strategies, recency-boosted search, or MCP
require the self-hosted `opensource-agent-memory` backend.

| Example | Backend | Runner | What it shows |
|---------|---------|--------|---------------|
| [**Managed memory quickstart**](https://github.com/redis-developer/adk-redis/tree/main/examples/managed_memory_quickstart) | `redis-agent-memory` | `python main.py` | Smallest memory agent, on the managed backend. No Docker or Agent Memory Server. |
| [**Simple Redis memory**](https://github.com/redis-developer/adk-redis/tree/main/examples/simple_redis_memory) | `opensource-agent-memory` | `python main.py` | Minimal agent with `RedisSessionMemoryService` and `RedisLongTermMemoryService`, plus auto-summarization and extraction. |
| [**Fitness coach (MCP)**](https://github.com/redis-developer/adk-redis/tree/main/examples/fitness_coach_mcp) | `opensource-agent-memory` only | `adk web .` | MCP-based memory with `McpToolset` and Agent Memory Server. The managed backend has no MCP endpoint. |
| [**Travel agent (hybrid)**](https://github.com/redis-developer/adk-redis/tree/main/examples/travel_agent_memory_hybrid) | `opensource-agent-memory` | `python main.py` | Framework-managed sessions + memory with vector search over travel docs. |
| [**Travel agent (tools)**](https://github.com/redis-developer/adk-redis/tree/main/examples/travel_agent_memory_tools) | `opensource-agent-memory`, switchable | `adk web .` | Same travel agent using LLM-controlled memory tools instead of framework services. Set `REDIS_MEMORY_BACKEND` to switch backends. |

## Search

| Example | Runner | What it shows |
|---------|--------|---------------|
| [**Redis search tools**](https://github.com/redis-developer/adk-redis/tree/main/examples/redis_search_tools) | `adk web .` | Vector, text, and range search tools in one agent. |
| [**SQL search**](https://github.com/redis-developer/adk-redis/tree/main/examples/redis_sql_search) | `adk web .` | `RedisSQLSearchTool` answering catalog questions via parameterized SQL. |
| [**RedisVL MCP search**](https://github.com/redis-developer/adk-redis/tree/main/examples/redisvl_mcp_search) | `adk web .` | Same knowledge base served via `rvl mcp` over MCP. |

## Semantic Caching

| Example | Runner | What it shows |
|---------|--------|---------------|
| [**Semantic cache (RedisVL)**](https://github.com/redis-developer/adk-redis/tree/main/examples/semantic_cache) | `python main.py` | Self-hosted semantic cache with `RedisVLCacheProvider`. |
| [**LangCache cache**](https://github.com/redis-developer/adk-redis/tree/main/examples/langcache_cache) | `python main.py` | Managed semantic cache with `LangCacheProvider`. |
