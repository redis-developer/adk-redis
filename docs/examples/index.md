---
description: Worked agents built with adk-redis and the Google ADK.
---

# Examples

Runnable agents built with the Google ADK and Redis. Each links to its source
directory and explains what it demonstrates.

## Memory and Sessions

| Example | What it shows |
|---------|---------------|
| [**Simple Redis memory**](https://github.com/redis-developer/adk-redis/tree/main/examples/simple_redis_memory) | Minimal agent with `RedisWorkingMemorySessionService` and `RedisLongTermMemoryService`. |
| [**Fitness coach (MCP)**](https://github.com/redis-developer/adk-redis/tree/main/examples/fitness_coach_mcp) | MCP-based memory with `McpToolset` and Agent Memory Server. |
| [**Travel agent (hybrid)**](https://github.com/redis-developer/adk-redis/tree/main/examples/travel_agent_memory_hybrid) | Framework-managed sessions + memory with vector search over travel docs. |
| [**Travel agent (tools)**](https://github.com/redis-developer/adk-redis/tree/main/examples/travel_agent_memory_tools) | Same travel agent using LLM-controlled memory tools instead of framework services. |

## Search

| Example | What it shows |
|---------|---------------|
| [**Redis search tools**](https://github.com/redis-developer/adk-redis/tree/main/examples/redis_search_tools) | Vector, text, and range search tools in one agent. |
| [**SQL search**](https://github.com/redis-developer/adk-redis/tree/main/examples/redis_sql_search) | `RedisSQLSearchTool` answering catalog questions via parameterized SQL. |
| [**RedisVL MCP search**](https://github.com/redis-developer/adk-redis/tree/main/examples/redisvl_mcp_search) | Same knowledge base served via `rvl mcp` over MCP. |

## Semantic Caching

| Example | What it shows |
|---------|---------------|
| [**Semantic cache (RedisVL)**](https://github.com/redis-developer/adk-redis/tree/main/examples/semantic_cache) | Self-hosted semantic cache with `RedisVLCacheProvider`. |
| [**LangCache cache**](https://github.com/redis-developer/adk-redis/tree/main/examples/langcache_cache) | Managed semantic cache with `LangCacheProvider`. |
