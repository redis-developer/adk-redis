# memory

## memory

Redis memory services for ADK.

### RedisLongTermMemoryService

```python
RedisLongTermMemoryService(config: RedisLongTermMemoryServiceConfig | None = None)
```

Bases: `BaseMemoryService`

Long-term memory service implementation using Redis Agent Memory Server.

This service provides production-grade memory capabilities including:

- Two-tier memory architecture (working memory + long-term memory)
- Automatic memory extraction (semantic facts, episodic events, preferences)
- Topic and entity extraction
- Auto-summarization when context window is exceeded
- Recency-boosted semantic search
- Deduplication and memory compaction
- https://github.com/redis/agent-memory-server

Requires the `agent-memory-client` package to be installed.

Example

```python
from adk_redis import (
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
)

config = RedisLongTermMemoryServiceConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    recency_boost=True,
)
memory_service = RedisLongTermMemoryService(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    memory_service=memory_service,
)
```

Initialize the Redis Long-Term Memory Service.

Parameters:

| Name     | Type                               | Description | Default                                                |
| -------- | ---------------------------------- | ----------- | ------------------------------------------------------ |
| `config` | \`RedisLongTermMemoryServiceConfig | None\`      | Configuration for the service. If None, uses defaults. |

Raises:

| Type          | Description                                      |
| ------------- | ------------------------------------------------ |
| `ImportError` | If agent-memory-client package is not installed. |

Source code in `src/adk_redis/memory/long_term_memory.py`

```python
def __init__(self, config: RedisLongTermMemoryServiceConfig | None = None):
  """Initialize the Redis Long-Term Memory Service.

  Args:
      config: Configuration for the service. If None, uses defaults.

  Raises:
      ImportError: If agent-memory-client package is not installed.
  """
  self._config = config or RedisLongTermMemoryServiceConfig()
```

#### add_session_to_memory

```python
add_session_to_memory(session: 'Session') -> None
```

Add a session's events to the Agent Memory Server.

Converts ADK Session events to WorkingMemory messages and stores them in the Agent Memory Server. The server will automatically:

- Extract semantic and episodic memories based on the configured strategy
- Perform topic and entity extraction
- Summarize context when the token limit is exceeded
- Promote memories to long-term storage via background tasks

Parameters:

| Name      | Type        | Description                                 | Default    |
| --------- | ----------- | ------------------------------------------- | ---------- |
| `session` | `'Session'` | The ADK Session containing events to store. | *required* |

Source code in `src/adk_redis/memory/long_term_memory.py`

```python
@override
async def add_session_to_memory(self, session: "Session") -> None:
  """Add a session's events to the Agent Memory Server.

  Converts ADK Session events to WorkingMemory messages and stores them
  in the Agent Memory Server. The server will automatically:
  - Extract semantic and episodic memories based on the configured strategy
  - Perform topic and entity extraction
  - Summarize context when the token limit is exceeded
  - Promote memories to long-term storage via background tasks

  Args:
      session: The ADK Session containing events to store.
  """
  try:
    working_memory = self._build_working_memory(session)

    if not working_memory.messages:
      logger.debug("No messages to store for session %s", session.id)
      return

    response = await self._client.put_working_memory(
        session_id=session.id,
        memory=working_memory,
        user_id=session.user_id,
    )

    logger.info(
        "Stored %d messages for session %s (context: %.1f%% used)",
        len(working_memory.messages),
        session.id,
        response.context_percentage_total_used or 0,
    )

  except Exception as e:
    logger.error(
        "Failed to add session %s to memory: %s",
        session.id,
        e,
    )
```

#### search_memory

```python
search_memory(*, app_name: str, user_id: str, query: str) -> SearchMemoryResponse
```

Search for memories using the Agent Memory Server.

Performs semantic search against long-term memory with optional recency boosting. Results are filtered by namespace (derived from app_name) and user_id.

Parameters:

| Name       | Type  | Description                                                 | Default    |
| ---------- | ----- | ----------------------------------------------------------- | ---------- |
| `app_name` | `str` | The application name (used as namespace if not configured). | *required* |
| `user_id`  | `str` | The user ID to filter memories.                             | *required* |
| `query`    | `str` | The search query for semantic matching.                     | *required* |

Returns:

| Type                   | Description                                                   |
| ---------------------- | ------------------------------------------------------------- |
| `SearchMemoryResponse` | SearchMemoryResponse containing matching MemoryEntry objects. |

Source code in `src/adk_redis/memory/long_term_memory.py`

```python
@override
async def search_memory(
    self, *, app_name: str, user_id: str, query: str
) -> SearchMemoryResponse:
  """Search for memories using the Agent Memory Server.

  Performs semantic search against long-term memory with optional
  recency boosting. Results are filtered by namespace (derived from
  app_name) and user_id.

  Args:
      app_name: The application name (used as namespace if not configured).
      user_id: The user ID to filter memories.
      query: The search query for semantic matching.

  Returns:
      SearchMemoryResponse containing matching MemoryEntry objects.
  """
  try:
    recency_config = (
        self._build_recency_config() if self._config.recency_boost else None
    )

    namespace = self._config.default_namespace or app_name

    results = await self._client.search_long_term_memory(
        text=query,
        namespace={"eq": namespace},
        user_id={"eq": user_id},
        distance_threshold=self._config.distance_threshold,
        recency=recency_config,
        limit=self._config.search_top_k,
    )

    memories = []
    for record in results.memories:
      content = types.Content(parts=[types.Part(text=record.text)])
      memory_entry = MemoryEntry(content=content)
      memories.append(memory_entry)

    logger.info(
        "Found %d memories for query '%s' (namespace=%s, user=%s)",
        len(memories),
        query[:50],
        namespace,
        user_id,
    )
    return SearchMemoryResponse(memories=memories)

  except Exception as e:
    logger.error("Failed to search memories: %s", e)
    return SearchMemoryResponse(memories=[])
```

#### close

```python
close() -> None
```

Close the memory service and cleanup resources.

Source code in `src/adk_redis/memory/long_term_memory.py`

```python
async def close(self) -> None:
  """Close the memory service and cleanup resources."""
  if "_client" in self.__dict__:
    # Check for initialized client without triggering cached_property
    await self._client.close()
    # Clear the cached property
    del self._client
```

### RedisLongTermMemoryServiceConfig

Bases: `BaseModel`

Configuration for Redis Long-Term Memory Service.

Attributes:

| Name                         | Type                                                      | Description                                                          |
| ---------------------------- | --------------------------------------------------------- | -------------------------------------------------------------------- |
| `api_base_url`               | `str`                                                     | Base URL of the Agent Memory Server.                                 |
| `timeout`                    | `float`                                                   | HTTP request timeout in seconds.                                     |
| `default_namespace`          | \`str                                                     | None\`                                                               |
| `search_top_k`               | `int`                                                     | Maximum number of memories to retrieve per search.                   |
| `distance_threshold`         | \`float                                                   | None\`                                                               |
| `recency_boost`              | `bool`                                                    | Enable recency-aware re-ranking of search results.                   |
| `semantic_weight`            | `float`                                                   | Weight for semantic similarity in recency boosting (0.0-1.0).        |
| `recency_weight`             | `float`                                                   | Weight for recency score in recency boosting (0.0-1.0).              |
| `freshness_weight`           | `float`                                                   | Weight for freshness component within recency score.                 |
| `novelty_weight`             | `float`                                                   | Weight for novelty component within recency score.                   |
| `half_life_last_access_days` | `float`                                                   | Half-life in days for last_accessed decay.                           |
| `half_life_created_days`     | `float`                                                   | Half-life in days for created_at decay.                              |
| `extraction_strategy`        | `Literal['discrete', 'summary', 'preferences', 'custom']` | Memory extraction strategy (discrete, summary, preferences, custom). |
| `extraction_strategy_config` | `dict[str, Any]`                                          | Additional configuration for the extraction strategy.                |
| `model_name`                 | \`str                                                     | None\`                                                               |
| `context_window_max`         | \`int                                                     | None\`                                                               |
