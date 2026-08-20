# Changelog

All notable changes to `adk-redis` are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.0.10] - 2026-08-20

### Added

- `RedisVLCacheProviderConfig.create_index` lets `RedisVLCacheProvider`
  attach to a search index provisioned outside adk-redis. With
  `create_index=False` construction issues no index command, so the cache
  runs on a credential denied `FT.INFO` and `FT.CREATE`. Requires
  `redisvl>=0.26.0`; the package floor stays at 0.18.2 and the default path
  is unchanged.
- `RedisVLCacheProviderConfig.overwrite` exposes index overwrite as a
  configuration option. It cannot be combined with `create_index=False`;
  that pairing raises a `ValueError` at construction.
- `ignore_errors` on `LLMResponseCacheConfig` and `ToolCacheConfig`
  defaults to True, logging cache backend failures and carrying on. Set it
  to False while developing to raise instead of reading a log line.

### Changed

- **Breaking:** `RedisVLCacheProvider` no longer forces `overwrite=True`.
  The default is now `False`, matching RedisVL, so an existing index is
  reused instead of dropped and recreated on every construction. If your
  index schema no longer matches the provider config, construction now
  raises a `ValueError` naming `overwrite` where it previously rebuilt the
  index silently and left entries embedded by the old model unindexed. To
  migrate, set `overwrite=True` for one deployment to rebuild the index, or
  drop it out of band with `FT.DROPINDEX <name>`.
- `LLMResponseCache` and `ToolCache` no longer let a cache backend failure
  abort the agent turn. A failed lookup falls through to the model or the
  tool, and a failed write returns the response unchanged, both logged.
  Previously any provider exception propagated out of the ADK callback and
  ended the invocation with no events emitted.
- Errors raised while RedisVL sets up the index are re-raised naming the
  `RedisVLCacheProviderConfig` field that resolves them. A credential
  denied `FT.INFO` is now pointed at `create_index`, and a drifted schema
  at `overwrite`.
- `RedisVLCacheProvider.clear()` deletes entries by scanning the cache key
  prefix when `create_index=False`, because RedisVL refuses index-wide
  destructive calls for an index it does not manage. The external index is
  never dropped.

### Fixed

- `RedisVLCacheProvider.close()` no longer raises `AttributeError` when the
  provider never opened a connection, which is reachable with
  `create_index=False` because construction sends nothing to Redis.
- `RedisVLCacheProvider.clear()` no longer builds its key scan from an
  unescaped cache name. A name containing a glob metacharacter, such as
  `cache[ab]`, matched unrelated keys and deleted them while leaving the
  cache's own entries in place.
- Integration tests now run in CI, which had no Redis service, so the
  suite silently skipped every test requiring one.
- Loggers are no longer named with a doubled package prefix. Every module
  built its logger as `"adk_redis." + __name__` while `__name__` already
  began with `adk_redis`, so the real logger was
  `adk_redis.adk_redis.cache.llm_cache` and configuring
  `adk_redis.cache` had no effect. Filtering on the top-level `adk_redis`
  logger is unchanged.

### Documentation

- New managed memory quickstart example, the smallest memory agent on the
  managed `redis-agent-memory` backend, with no Docker or Agent Memory
  Server required.
- The examples index labels every example with its memory backend and its
  runner, making clear which examples require the self-hosted
  `opensource-agent-memory` backend.
- The caching guides cover `create_index`, `overwrite`, and
  `ignore_errors`.

## [0.0.9] - 2026-07-31

### Added

- Cache providers now expose stable entry IDs from `check()` and `store()` and
  support targeted invalidation through `delete_by_id()` without clearing
  unrelated entries.
- Memory tools resolve the acting user from the ADK `tool_context` before
  falling back to configured defaults, allowing a shared runner to remain
  scoped to each invocation user.
- `CreateMemoryTool.run_async()` accepts an application-supplied `id` for
  idempotent managed-memory writes. IDs are derived with namespace and user
  scope to prevent cross-tenant collisions and are not exposed to the LLM.

### Changed

- The managed memory integration now requires `redis-agent-memory>=0.2.0`.
  SDK method compatibility was verified across session memory, long-term
  memory, and memory tools.
- Documentation now covers cache entry IDs, targeted invalidation,
  invocation-user resolution, scoped client IDs, and the updated managed SDK
  requirement.

### Fixed

- Update and delete memory tools validate namespace and user ownership before
  mutating records. Delete preflight reads use bounded concurrency.
- Self-hosted memory warnings no longer log raw application-supplied IDs.

## [0.0.8] - 2026-06-24

### Changed

- Renamed `RedisWorkingMemorySessionService` to `RedisSessionMemoryService`
  and `RedisWorkingMemorySessionServiceConfig` to
  `RedisSessionMemoryServiceConfig`, aligning with the managed Redis Agent
  Memory "session memory" terminology and ADK's `<Backend>SessionService`
  convention. The module `adk_redis.sessions.working_memory` moved to
  `adk_redis.sessions.session_memory`. Docs and examples now use the new
  names.

### Deprecated

- `RedisWorkingMemorySessionService` and
  `RedisWorkingMemorySessionServiceConfig` remain as deprecated aliases that
  emit a `DeprecationWarning` and will be removed in 0.1.0. Switch to
  `RedisSessionMemoryService` / `RedisSessionMemoryServiceConfig`.
- The old module path `adk_redis.sessions.working_memory` remains as a
  compatibility shim that re-exports the classes and emits a
  `DeprecationWarning` on import. It will be removed in 0.1.0. Import from
  `adk_redis.sessions.session_memory` or the top-level `adk_redis` package.

## [0.0.7] - 2026-06-18

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
- Public backend selectors `REDIS_AGENT_MEMORY_BACKEND`,
  `OPENSOURCE_AGENT_MEMORY_BACKEND`, and the `MemoryBackendName` type are
  re-exported from `adk_redis` and `adk_redis.memory` for typo-safe backend
  selection.
- New `managed_memory_quickstart` example demonstrating the managed
  `redis-agent-memory` backend wired through `get_service_registry()`.

### Fixed

- `UpdateMemoryTool` now applies the configured `default_namespace`,
  `default_owner_id`, and `default_user_id` when the caller omits them on the
  managed `redis-agent-memory` backend.
- `RedisLongTermMemoryService` derives the events memory ID from event ids and
  timestamps instead of `len(events)`, preventing collisions between distinct
  event batches of equal length.
- Session and namespace identifiers are sanitized for the managed backend,
  which rejects `-` and `:` characters and enforces length limits; empty
  sessions are returned before the first event so the first message can flow.

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
- New how-to `docs/user_guide/how_to_guides/managed_memory_setup.md` for the
  managed Redis Agent Memory backend, wired into the nav and how-to index. Adds
  a Prerequisites/install line and a "Get credentials" section pointing to the
  Redis Cloud Agent Memory create-service, view-service, and use-API pages.
- Reconciled environment variable names to the canonical `REDIS_AGENT_MEMORY_*`
  (with `AGENT_MEMORY_*` fallbacks) across `docs/user_guide/01_integration.md`,
  the `simple_redis_memory` example (`main.py` + README), and the integration
  tests.
- README documents the `managed_memory_quickstart` example and clarifies which
  examples run via `python main.py` versus `adk web`.

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
