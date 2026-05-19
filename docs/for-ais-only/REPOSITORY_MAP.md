# Repository Map

A module-by-module guide to the `adk-redis` source tree, written for an
agent that needs to change something and wants to know where to look.

> Style: this repo's `AGENTS.md` forbids em dashes and inline imports.
> Two-space indentation, Google-style docstrings, `make format` before
> committing.

## Source layout

```
src/adk_redis/
  __init__.py             Re-exports the full public surface (memory,
                          session, search, tool, and cache classes).
  _version.py             Build-time version string.
  sessions/
    __init__.py           Re-exports RedisWorkingMemorySessionService.
    working_memory.py     ADK BaseSessionService implementation backed by
                          Redis Agent Memory Server working memory.
  memory/
    __init__.py           Re-exports RedisLongTermMemoryService and the
                          memory tools (Memory Prompt / Search / Create /
                          Delete / Update).
    long_term_memory.py   ADK BaseMemoryService implementation backed by
                          Agent Memory Server long-term memory.
    _utils.py             Internal serialization and key helpers.
  tools/
    __init__.py           Re-exports the search tools.
    search/               RedisVL-backed vector, hybrid, range, BM25 text,
                          and SQL search tools (one ADK FunctionTool each).
    memory/               ADK FunctionTool wrappers around the memory
                          service (MemoryPromptTool, SearchMemoryTool,
                          CreateMemoryTool, DeleteMemoryTool,
                          UpdateMemoryTool).
    mcp_memory.py         MCP tool surface for the same memory operations
                          (Agent Memory Server).
    mcp_search.py         create_redisvl_mcp_toolset(...) for RedisVL's
                          own MCP server (rvl mcp). Supports stdio, sse,
                          streamable-http; bearer auth on HTTP transports.
  cache/
    __init__.py           Re-exports the cache providers.
    _provider.py          Provider protocol and base class.
    llm_cache.py          Wraps an LLM call site with semantic caching.
    tool_cache.py         Wraps a tool call site with semantic caching.
    callbacks.py          ADK callback hooks for cache integration.
```

## Test layout

```
tests/
  conftest.py                  Shared fixtures (fakeredis, fake AMS).
  test_imports.py              Smoke test for every public re-export.
  test_version.py              `__version__` is set.
  sessions/
    test_working_memory.py     RedisWorkingMemorySessionService end-to-end.
  memory/
    test_long_term_memory.py   RedisLongTermMemoryService end-to-end.
  tools/
    test_vector_search.py      RedisVectorSearchTool (incl. epsilon-removal
                               regression on RedisVectorQueryConfig).
    test_hybrid_search.py      RedisHybridSearchTool.
    test_range_search.py       RedisRangeSearchTool.
    test_text_search.py        RedisTextSearchTool.
    test_sql_search.py         RedisSQLSearchTool.
    test_mcp_search.py         create_redisvl_mcp_toolset (validation,
                               three transports, bearer auth, tool filter).
  cache/
    test_provider.py           RedisVLCacheProvider (incl. no-DeprecationWarning
                               regression for the cache.llm import path).
  integration/
    conftest.py                Skip-if-Redis-unreachable harness.
    test_search_tools_end_to_end.py    Real Redis 8.4: vector/text/range/
                                       native hybrid round-trips.
    test_sql_and_cache_end_to_end.py   Real Redis 8.4: SQL SELECT with
                                       params, cache round-trip.
    test_adk_agent_registration.py     Tools register with google.adk.Agent
                                       and surface via canonical_tools().
```

## Where features live

| Feature | Module(s) |
|---|---|
| Working-memory session storage | `sessions/working_memory.py` |
| Long-term memory + Memory Server proxy | `memory/long_term_memory.py`, `memory/_utils.py` |
| ADK Memory tools (FunctionTool wrappers) | `tools/memory/` |
| MCP memory tool surface (Agent Memory Server) | `tools/mcp_memory.py` |
| MCP search tool surface (RedisVL MCP server) | `tools/mcp_search.py` |
| Vector / Hybrid / Range / Text / SQL search tools | `tools/search/` |
| LLM and tool semantic caching | `cache/llm_cache.py`, `cache/tool_cache.py` |
| Cache provider abstraction (RedisVL / LangCache) | `cache/_provider.py` |
| ADK callback hooks for caching | `cache/callbacks.py` |

## What to read before changing X

- **A search tool.** Each tool under `tools/search/` is an ADK
  `FunctionTool` plus a thin RedisVL query. Tools are independent; copy
  the closest existing one. Wire it through `tools/__init__.py` and the
  re-export in `adk_redis/__init__.py`.
- **The session service.** `sessions/working_memory.py` implements ADK's
  `BaseSessionService`. It calls Agent Memory Server working-memory
  endpoints; do not reach into Redis directly from the session layer.
- **The memory service.** `memory/long_term_memory.py` implements ADK's
  `BaseMemoryService`. The memory tools under `tools/memory/` are thin
  `FunctionTool` wrappers and must keep parameter names aligned with
  the underlying service methods (the LLM picks them by name).
- **A cache provider.** Add a class implementing the protocol in
  `cache/_provider.py`, register it in `cache/__init__.py`, and add
  callback hookup in `cache/callbacks.py` if it should be invoked
  automatically by ADK lifecycle events.

## What is intentionally not exported

- `memory/_utils.py` is internal serialization; do not import it from
  application code.
- `cache/_provider.py` exposes the protocol and base class but the
  individual providers (`RedisVLCacheProvider`, `LangCacheProvider`) are
  the public surface.
- Test fixtures and fakes under `tests/` are not part of the public API.
