# Changelog

All notable changes to `adk-redis` are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
- `create_redisvl_mcp_toolset(...)` (`adk_redis.tools.mcp_search`): helper
  that returns an ADK `McpToolset` wired to RedisVL's own MCP server
  (`rvl mcp`). Supports `stdio`, `sse`, and `streamable-http` transports;
  bearer auth on HTTP transports; `--read-only` default for stdio.
  Installed via the new `adk-redis[mcp-search]` extra
  (`redisvl[mcp]>=0.18.2`).
- Module constants `REDISVL_MCP_TOOL_SEARCH` and `REDISVL_MCP_TOOL_UPSERT`
  for symbolic tool filtering.
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
- New unit tests for `RedisSQLSearchTool` (`tests/tools/test_sql_search.py`)
  and `create_redisvl_mcp_toolset` (`tests/tools/test_mcp_search.py`).
- New integration suite under `tests/integration/` that round-trips
  vector, text, range, native hybrid, and SQL queries plus a cache
  round-trip against a real Redis 8.4 container, and confirms tools
  register cleanly with `google.adk.Agent`.
