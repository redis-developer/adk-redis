# Handover: memory example coverage and runner alignment

Status: open follow-up after PR #16 (selectable memory backends, release 0.0.7).

## Background

PR #16 made the memory stack backend-pluggable through a single config field:

- `backend="redis-agent-memory"` (managed Redis Agent Memory, library default).
- `backend="opensource-agent-memory"` (self-hosted Agent Memory Server via
  `agent-memory-client`).

See [`redis-agent-memory-default.md`](redis-agent-memory-default.md) for the
backend selection design.

The work below is open because the two backends do not have identical
capabilities, and the shipped examples were originally written against the
opensource backend. Before changing examples, the next person needs to
confirm what the managed backend can and cannot do today, then decide what
the example surface should look like.

## Goal

Decide what `examples/` should look like now that two memory backends are
supported. Produce a concrete plan (and ideally PRs) that aligns examples
with the library default, covers both backends honestly, and keeps the
"clone, run, done" experience for new users.

## How to approach this

Work in two phases. Do not skip phase 1: the example decisions in phase 2
are downstream of what you find in phase 1.

### Phase 1: assess implementation coverage of the managed backend

Goal: a written answer to "does every ADK memory surface we ship work
end-to-end against `redis-agent-memory`, and if not, what is missing?"

1. Read the current backend dispatch:
   - `src/adk_redis/memory/long_term_memory.py`
   - `src/adk_redis/sessions/working_memory.py`
   - `src/adk_redis/tools/memory/` (all six tools plus `_base.py` and
     `_config.py`)
   - `src/adk_redis/memory/_backends.py`
2. Read the `redis-agent-memory` SDK surface that we actually call. The
   installed package lives under
   `.venv/lib/python3.13/site-packages/redis_agent_memory/`. Start at
   `sdk.py` (the `AgentMemory` class) and the `models/` directory.
3. Read the `agent-memory-client` surface we call for the opensource path,
   and the upstream `redis/agent-memory-server` README, so you know what
   the opensource backend offers that the managed SDK may not.
4. For each ADK surface we expose
   (`RedisLongTermMemoryService.add_session_to_memory` / `add_memory` /
   `add_events_to_memory` / `search_memory`,
   `RedisWorkingMemorySessionService.create_session` / `get_session` /
   `list_sessions` / `append_event` / `delete_session`, and each memory
   tool), record:
   - Does the managed SDK have a primitive we can call?
   - If yes, is the behavior equivalent, or is there a semantic gap
     (for example: explicit writes vs. server-side extraction,
     summarization, recency, MCP, namespace/scope semantics, owner
     IDs)?
   - If no, is it a hard gap (no managed equivalent exists) or a soft
     gap (managed has a different primitive that we have not wired
     yet)?
5. Cross-check against the existing live integration tests in
   `tests/integration/test_memory_backends_end_to_end.py`. Anything not
   exercised there is by definition not verified end-to-end on managed.

Deliverable: a coverage table (ADK surface x backend) checked into
`docs/specs/` or attached to the follow-up PR, plus a list of hard
gaps that need either upstream work in `redis-agent-memory` or
documentation in `adk-redis` so users are not surprised.

### Phase 2: assess example coverage given the phase 1 findings

Only start once phase 1 has a written conclusion. The example decisions
are different depending on whether managed has full parity, partial
parity, or a known feature gap.

1. Enumerate the current examples and what each one actually exercises:
   - Which use `RedisLongTermMemoryService` / `RedisWorkingMemorySessionService`?
   - Which use the memory tools directly?
   - Which use the Agent Memory Server MCP endpoint?
   - Which use the `adk web` runner vs. a custom `main.py` via
     `get_fast_api_app`?
   - Which default `REDIS_MEMORY_BACKEND` is set in `.env.example`,
     README, and agent wiring?
2. For each example, answer:
   - Can it run unchanged on managed today, given phase 1 findings?
   - If not, is the blocker an example-level wiring issue (env vars,
     defaults), a runner constraint (services need `get_fast_api_app`,
     `adk web` cannot register them), or a real feature gap in managed?
   - Should its default backend stay opensource, flip to managed, or be
     duplicated so both backends are covered?
3. Decide on the target example surface:
   - Do we need a new managed-default example? If yes, what runner and
     what feature set (services vs. tools-only)?
   - Do any existing examples need to be split, renamed, or removed?
   - Is there a missing top-level `examples/README.md` matrix that would
     orient users to the runner/backend/infra trade-offs?
   - Is `examples/simple_redis_memory/.env.example` (currently empty)
     intentional or an oversight?

Deliverable: a short plan ("add X, change Y, leave Z alone, document W")
and the corresponding PRs.

## Known starting observations

These are observations from the PR #16 review, included as a starting
point. Treat them as inputs to phase 1 / phase 2, not as conclusions.

- Every memory example currently defaults to
  `REDIS_MEMORY_BACKEND=opensource-agent-memory`, which is the opposite
  of the library default.
- Only one memory example (`travel_agent_memory_tools`) uses the
  `adk web` runner. The other two register services through
  `google.adk.cli.service_registry.get_service_registry()`, which only
  `get_fast_api_app` consults, so they ship a custom `main.py`. Whether
  this is a permanent constraint or something that should be lifted
  upstream in ADK is worth checking during phase 1.
- `fitness_coach_mcp` depends on the Agent Memory Server MCP endpoint.
  Confirm during phase 1 whether the managed backend exposes an
  equivalent today; if not, this example must stay on opensource and
  the handover doc / example README should say so.
- `examples/simple_redis_memory/.env.example` is empty.

## Out of scope for this handover

- Changing the library default backend.
- Live CI coverage for managed integration tests (covered separately by
  the integration tests added in PR #16; gating them in CI is its own
  follow-up).

## Pointers

- Backend selection spec: [`redis-agent-memory-default.md`](redis-agent-memory-default.md)
- Backend dispatch:
  - `src/adk_redis/memory/long_term_memory.py`
  - `src/adk_redis/sessions/working_memory.py`
  - `src/adk_redis/tools/memory/_config.py`
  - `src/adk_redis/tools/memory/_base.py`
- Live integration coverage: `tests/integration/test_memory_backends_end_to_end.py`
- Managed SDK (installed): `.venv/.../site-packages/redis_agent_memory/sdk.py`
- Opensource server: <https://github.com/redis/agent-memory-server>
- Example wiring references:
  - Tools-only + `adk web`: `examples/travel_agent_memory_tools/`
  - Services + custom runner: `examples/travel_agent_memory_hybrid/main.py`,
    `examples/simple_redis_memory/main.py`
  - MCP via opensource: `examples/fitness_coach_mcp/`
