# Handover: memory example coverage and runner alignment

Status: open follow-up after PR #16 (selectable memory backends, release 0.0.7).

## Context

PR #16 made the memory stack backend-pluggable:

- `backend="redis-agent-memory"` (managed, library default per
  [`redis-agent-memory-default.md`](redis-agent-memory-default.md)).
- `backend="opensource-agent-memory"` (self-hosted Agent Memory Server via
  `agent-memory-client`).

The library now defaults to managed Redis Agent Memory, but the shipped
examples do not reflect that default and do not exercise the managed
backend under the `adk web` runner.

## Current state of `examples/`

Memory-touching examples (3 of 9):

| Example | Runner | Default `REDIS_MEMORY_BACKEND` | Opensource AMS infra |
|---|---|---|---|
| `simple_redis_memory` | `main.py` via `get_fast_api_app` | `opensource-agent-memory` | `docker run` snippet in README |
| `travel_agent_memory_hybrid` | `main.py` via `get_fast_api_app` (README: "MUST use `main.py`, not `adk web`") | `opensource-agent-memory` | `docker-compose.yml` |
| `travel_agent_memory_tools` | `adk web .` (memory tools only) | `opensource-agent-memory` | `docker-compose.yml` |

`fitness_coach_mcp` also ships `agent-memory-server` for MCP toolset use
even though it is not a memory-backend example.

## Gaps

1. **No `redis-agent-memory` + `adk web` example.** The only `adk web`
   memory example (`travel_agent_memory_tools`) defaults to the
   opensource backend. Switching it works via env vars, but no example
   showcases the managed-default zero-infra path.
2. **Defaults disagree with the library.** Every memory example sets
   `REDIS_MEMORY_BACKEND=opensource-agent-memory` in `.env.example` and
   `os.getenv(..., "opensource-agent-memory")`. The library default is
   `redis-agent-memory`. New users following an example get the opposite
   of the documented default.
3. **`adk web` is structurally unavailable to two examples.**
   `simple_redis_memory` and `travel_agent_memory_hybrid` register
   `RedisWorkingMemorySessionService` and `RedisLongTermMemoryService`
   through `google.adk.cli.service_registry.get_service_registry()`,
   which only `get_fast_api_app` consults. `adk web` ignores the
   registry, so service-based examples are pinned to the custom
   FastAPI runner regardless of backend.
4. **Documentation gaps.**
   - `examples/simple_redis_memory/.env.example` is empty.
   - No top-level `examples/README.md` matrix to orient users to
     runner-vs-backend trade-offs.
   - The `adk web` constraint above is not written down anywhere.

## Recommended follow-ups

### 1. Add a managed-default `adk web` example

Create `examples/simple_managed_memory/` (working name) modeled after
`travel_agent_memory_tools`:

- Memory tools only (no service registration), so `adk web .` works.
- Defaults to `REDIS_MEMORY_BACKEND=redis-agent-memory`.
- `.env.example` highlights `AGENT_MEMORY_STORE_ID` and
  `AGENT_MEMORY_API_KEY` as primary inputs.
- No `docker-compose.yml`. README points at the managed Redis Agent
  Memory signup flow.
- README explicitly contrasts with `travel_agent_memory_tools` (same
  shape, opensource path) so users see the swap is a one-env-var change.

This closes both concerns (#1 and #2) with a single new example without
churning the existing three.

### 2. Decide on example defaults

Two viable options:

- **Option A (recommended):** keep existing examples on
  `opensource-agent-memory` defaults since they ship a local Docker
  workflow that works offline, and rely on the new managed example
  above for the library-default path. Add a one-line note in each
  README clarifying that the library default differs.
- **Option B:** flip every memory example default to
  `redis-agent-memory` to match the library. Requires every example to
  document store-ID / API-key acquisition up front, which raises the
  barrier to running them locally.

Option A keeps the "clone, `docker compose up`, run" loop intact for
existing examples and isolates the managed path to one purpose-built
example.

### 3. Documentation cleanups

- Backfill `examples/simple_redis_memory/.env.example` with the same
  variable set used by the other two memory examples.
- Add `examples/README.md` with a matrix: example, runner
  (`adk web` vs. `main.py`), backend default, infra required, primary
  feature demonstrated.
- Document the `adk web` vs. `get_fast_api_app` service-registry
  constraint in `docs/user_guide/how_to_guides/session_service.md` and
  `docs/concepts/sessions.md` so users understand why service-based
  examples ship a `main.py`.

### 4. Optional: rename for clarity

`travel_agent_memory_tools` and the proposed `simple_managed_memory`
would form a natural pair. Consider renaming on the next breaking-doc
pass to `travel_agent_memory_tools_opensource` and
`travel_agent_memory_tools_managed` (or similar) to make the
backend axis obvious from the directory name.

## Out of scope for this handover

- Changing the library default away from `redis-agent-memory`.
- Removing or consolidating existing examples.
- Adding live CI coverage for the managed example (covered separately
  by the integration tests added in PR #16).

## Pointers

- Spec: [`docs/specs/redis-agent-memory-default.md`](redis-agent-memory-default.md)
- Backend dispatch: `src/adk_redis/memory/long_term_memory.py`,
  `src/adk_redis/sessions/working_memory.py`,
  `src/adk_redis/tools/memory/_config.py`
- Example wiring reference: `examples/travel_agent_memory_tools/travel_agent/agent.py`
- Service-registry runner: `examples/travel_agent_memory_hybrid/main.py`
