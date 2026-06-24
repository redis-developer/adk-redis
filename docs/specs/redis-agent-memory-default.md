# Redis Agent Memory Dual Backend Spec

## Goal

Add Redis Agent Memory support to `adk-redis` while keeping the open source,
self-hosted Agent Memory Server path available. Users choose the backend with a
single config field.

## Backend Choice

All ADK memory surfaces accept:

```python
backend="redis-agent-memory"   # default, uses redis-agent-memory
backend="opensource-agent-memory"  # self-hosted, uses agent-memory-client
```

The public class names stay unchanged:

- `RedisSessionMemoryService`
- `RedisLongTermMemoryService`
- `MemoryToolConfig`
- `SearchMemoryTool`, `CreateMemoryTool`, `GetMemoryTool`,
  `UpdateMemoryTool`, `DeleteMemoryTool`, `MemoryPromptTool`

## ADK Upstream Check

The latest `google/adk-python` source was checked from a fresh shallow clone at
commit `ae95a97`. The memory service contract still includes
`add_session_to_memory()` and `search_memory()`, and now also includes optional
write paths:

- `add_events_to_memory()`
- `add_memory()`

The implementation supports these newer hooks while remaining compatible with
installed ADK versions that do not call them yet.

## Redis Agent Memory Backend

The default backend uses `redis_agent_memory.AgentMemory`.

Session service:

- `append_event()` writes Redis Agent Memory session events.
- `get_session()` reconstructs ADK sessions from stored events.
- `list_sessions()` stores ADK scope in deterministic internal session IDs.

Long-term memory service:

- `search_memory()` calls `search_long_term_memory_async()`.
- Searches filter by `ownerId == user_id` and namespace.
- `add_memory()` writes durable `semantic`, `episodic`, or `message` records.
- `add_events_to_memory()` and `add_session_to_memory()` write ADK events as
  long-term `message` memories for ADK compatibility.

Tools:

- Use the async Redis Agent Memory SDK methods for search, create, get, update,
  delete, and prompt enrichment.
- `default_owner_id` is available for tools that run outside an ADK user
  context.

## Agent Memory Server Backend

The self-hosted backend keeps the previous `agent-memory-client` behavior.

Session service:

- Uses Working Memory APIs.
- Preserves automatic summarization and extraction strategy settings.
- Keeps incremental `append_messages_to_working_memory()` writes.

Long-term memory service:

- `add_session_to_memory()` stores session working memory so the server can
  extract long-term memories.
- `add_memory()` uses `add_memory_tool()` for explicit durable memory writes.
- `search_memory()` uses `search_long_term_memory()` with namespace and user
  filters, plus optional recency config.

Tools:

- Use the previous REST client methods.
- Preserve recency settings and memory prompt behavior.

## Configuration

Shared options:

- `backend`
- `api_base_url`
- `default_namespace`
- `search_top_k`
- `distance_threshold`
- `timeout`

Redis Agent Memory options:

- `api_key`
- `store_id`
- `timeout_ms`
- `similarity_threshold`
- `default_owner_id` for tools

Agent Memory Server options:

- `recency_boost`
- `semantic_weight`
- `recency_weight`
- `freshness_weight`
- `novelty_weight`
- `half_life_last_access_days`
- `half_life_created_days`
- `extraction_strategy`
- `extraction_strategy_config`
- `model_name`
- `context_window_max`

## Dependency

The `memory` extra installs both backend clients:

- `agent-memory-client>=0.14.0`
- `redis-agent-memory>=0.0.4`

## Tests

Unit tests mock both clients and cover:

- Config defaults.
- Redis Agent Memory owner and namespace filters.
- Self-hosted Agent Memory Server backend dispatch.
- Redis Agent Memory session event writes.
- Session reconstruction.
- Tool create, search, update, and delete payloads.

Normal unit tests do not require a live memory server.
