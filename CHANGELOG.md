# Changelog

All notable changes to `adk-redis` are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.0.7] - 2026-06-02

### Added

- Selectable memory backend support across all ADK memory surfaces.
  `RedisLongTermMemoryService`, `RedisWorkingMemorySessionService`,
  and the six memory tools (`SearchMemoryTool`, `CreateMemoryTool`,
  `GetMemoryTool`, `UpdateMemoryTool`, `DeleteMemoryTool`,
  `MemoryPromptTool`) now accept a `backend` field:
  - `backend="redis-agent-memory"` (default) routes through the managed
    `redis-agent-memory` SDK.
  - `backend="opensource-agent-memory"` keeps the self-hosted Agent
    Memory Server path through `agent-memory-client`.
- `RedisLongTermMemoryService` now implements the newer ADK write hooks
  `add_events_to_memory()` and `add_memory()`, verified against upstream
  `google/adk-python@ae95a97`. Older ADK versions that only call
  `add_session_to_memory()` and `search_memory()` keep working.
- New spec at `docs/specs/redis-agent-memory-default.md` describing the
  dual-backend design, config surface, and test scope.
- Examples (`simple_redis_memory`, `travel_agent_memory_hybrid`,
  `travel_agent_memory_tools`) surface a `REDIS_MEMORY_BACKEND` env
  var in `.env.example`, README, and agent wiring so users can switch
  backends without code changes.
- `tests/integration/test_memory_backends_end_to_end.py`: live
  round-trip coverage for both backends. Skips when
  `REDIS_AGENT_MEMORY_API_BASE_URL` / `REDIS_AGENT_MEMORY_API_KEY` /
  `REDIS_AGENT_MEMORY_STORE_ID` or `AGENT_MEMORY_SERVER_URL` are not
  set.

### Changed

- `memory` extra now installs both `agent-memory-client>=0.14.0` and
  `redis-agent-memory>=0.0.4`.
- CI workflow (`.github/workflows/ci.yml`) now invokes the
  `format-check`, `lint`, and `type-check` Make targets so the
  Makefile is the single source of truth for local and CI checks.

### Docs

- Updated `docs/concepts/memory.md`, `docs/concepts/sessions.md`, and
  the `docs/user_guide/` how-to guides for `memory_service`,
  `session_service`, `memory_server_setup`, and `redis_setup` to
  reflect the backend choice.

## [0.0.6] - 2026-05-20

### Breaking

- Removed `create_memory_mcp_toolset()` and all MCP wrapper constants
  (`ALL_MCP_TOOLS`, `MCP_TOOL_*`) from the package. Use ADK's native
  `McpToolset` with `SseConnectionParams` pointed at the Agent Memory
  Server `/sse` endpoint instead. This aligns AMS MCP wiring with the
  standard pattern used by all other ADK catalog integrations.

### Changed

- Updated `fitness_coach_mcp` example to use native `McpToolset` +
  `SseConnectionParams` directly.

## [0.0.5] - 2026-05-19

### Breaking

- Removed `epsilon` from `RedisVectorQueryConfig`. `EPSILON` is a
  `VECTOR_RANGE`-only attribute that Redis rejects when emitted in a KNN
  bracket. Range searches keep the field on `RedisRangeQueryConfig`. Users
  who set `epsilon=...` on a KNN config must drop it.

### Added

- `RedisSQLSearchTool` (`adk_redis.tools.search.sql`): new search tool
  wrapping `redisvl.query.SQLQuery`. Lets agents emit SQL `SELECT`
  statements (with optional `params` for placeholders) against a bound
  Redis index. Installed via the new `adk-redis[sql]` extra
  (`redisvl[sql-redis]>=0.18.2`).
- New `examples/redisvl_mcp_search/`: the MCP-path mirror of
  `examples/redis_search_tools/`. Same knowledge-base corpus, served by
  a `rvl mcp` server in hybrid (BM25 + vector) mode; the agent connects
  via ADK's standard `McpToolset`. No adk-redis wrapper is needed; users
  wire `StdioConnectionParams` / `SseConnectionParams` /
  `StreamableHTTPConnectionParams` directly, matching the pattern used
  by every catalog MCP integration page.
- `make redis-up` / `make redis-down` / `make test-integration` targets
  for the new `tests/integration/` suite. Integration tests skip
  cleanly when no Redis with the RediSearch module is reachable at
  `$REDIS_URL` (default `redis://localhost:6399`).

### Changed

- Bumped the `redisvl` floor in the `search` and `langcache` extras to
  `>=0.18.2`.
- Migrated the semantic cache import in `cache/_provider.py` from the
  deprecated `redisvl.extensions.llmcache` path to the canonical
  `redisvl.extensions.cache.llm`. The old path was emitting a
  `DeprecationWarning` on import.

### Tests

- TDD-first regression coverage for the epsilon removal
  (`tests/tools/test_vector_search.py::TestRedisVectorQueryConfigEpsilonRemoval`).
- New cache provider tests (`tests/cache/test_provider.py`) including
  a no-`DeprecationWarning` assertion on the import path.
- New unit tests for `RedisSQLSearchTool`
  (`tests/tools/test_sql_search.py`).
- New integration suite under `tests/integration/` that round-trips
  vector, text, range, native hybrid, and SQL queries plus a cache
  round-trip against a real Redis 8.4 container, and confirms tools
  register cleanly with `google.adk.Agent`.
