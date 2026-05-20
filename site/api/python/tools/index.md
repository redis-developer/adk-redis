# tools

## tools

Redis tools for ADK.

### CreateMemoryTool

```python
CreateMemoryTool(*, config: MemoryToolConfig | None = None, name: str = 'create_memory', description: str = 'Creates a new long-term memory. Use this when the user asks you to remember something.')
```

Bases: `BaseMemoryTool`

Tool for creating new long-term memories.

This tool allows the LLM to explicitly store information in long-term memory. Use this when the user asks to remember something specific.

Example

```python
from adk_redis.tools.memory import CreateMemoryTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
tool = CreateMemoryTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Create Memory Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                    |
| ------------- | ------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                        |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'create_memory'`                                                                          |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Creates a new long-term memory. Use this when the user asks you to remember something.'` |

Source code in `src/adk_redis/tools/memory/create.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "create_memory",
    description: str = (
        "Creates a new long-term memory. "
        "Use this when the user asks you to remember something."
    ),
):
  """Initialize the Create Memory Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Create a new long-term memory.

Parameters:

| Name          | Type | Description                                   | Default    |
| ------------- | ---- | --------------------------------------------- | ---------- |
| `content`     |      | The content of the memory to store.           | *required* |
| `topics`      |      | Optional list of topics/tags.                 | *required* |
| `memory_type` |      | Type of memory (semantic, episodic, message). | *required* |
| `namespace`   |      | Optional namespace override.                  | *required* |
| `user_id`     |      | Optional user ID override.                    | *required* |

Returns:

| Type             | Description                             |
| ---------------- | --------------------------------------- |
| `dict[str, Any]` | A dictionary with status and memory_id. |

Source code in `src/adk_redis/tools/memory/create.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Create a new long-term memory.

  Args:
      content: The content of the memory to store.
      topics: Optional list of topics/tags.
      memory_type: Type of memory (semantic, episodic, message).
      namespace: Optional namespace override.
      user_id: Optional user ID override.

  Returns:
      A dictionary with status and memory_id.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  content = args.get("content")
  topics = args.get("topics", [])
  memory_type_raw = args.get("memory_type", "semantic")
  namespace = self._get_namespace(args.get("namespace"))
  user_id = self._get_user_id(args.get("user_id"))

  if not content:
    return {"status": "error", "message": "content is required"}

  # Map invalid memory types to valid ones
  # Valid types: 'semantic', 'episodic', 'message'
  memory_type_map = {
      "preference": "semantic",
      "fact": "semantic",
      "event": "episodic",
      "experience": "episodic",
      "conversation": "message",
  }
  memory_type = memory_type_map.get(memory_type_raw, memory_type_raw)
  if memory_type not in ("semantic", "episodic", "message"):
    memory_type = "semantic"  # Default fallback

  try:
    # Use add_memory_tool which creates a memory in a session context
    # We'll use a temporary session ID for standalone memory creation
    import uuid

    session_id = f"standalone_{uuid.uuid4().hex[:8]}"

    client = self._get_client()
    response = await client.add_memory_tool(
        session_id=session_id,
        text=content,
        memory_type=memory_type,
        topics=topics if topics else None,
        namespace=namespace,
        user_id=user_id,
    )

    # Response is a dict with 'success' key and summary
    if response.get("success"):
      # Extract memory ID from summary if available, or use session_id as fallback
      memory_id = response.get("memory_id", session_id)
      return {
          "status": "success",
          "memory_id": memory_id,
          "message": response.get("summary", "Memory created successfully"),
      }
    else:
      return {
          "status": "error",
          "message": response.get("summary", "Failed to create memory"),
      }

  except Exception as e:
    logger.error("Failed to create memory: %s", e)
    return {
        "status": "error",
        "message": f"Failed to create memory: {str(e)}",
    }
```

### DeleteMemoryTool

```python
DeleteMemoryTool(*, config: MemoryToolConfig | None = None, name: str = 'delete_memory', description: str = 'Deletes one or more long-term memories by ID. Use this when the user asks you to forget something.')
```

Bases: `BaseMemoryTool`

Tool for deleting long-term memories.

This tool allows the LLM to delete specific memories by ID. Use this when the user asks to forget something.

Example

```python
from adk_redis.tools.memory import DeleteMemoryTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
tool = DeleteMemoryTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Delete Memory Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                                |
| ------------- | ------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                                    |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'delete_memory'`                                                                                      |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Deletes one or more long-term memories by ID. Use this when the user asks you to forget something.'` |

Source code in `src/adk_redis/tools/memory/delete.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "delete_memory",
    description: str = (
        "Deletes one or more long-term memories by ID. "
        "Use this when the user asks you to forget something."
    ),
):
  """Initialize the Delete Memory Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Delete long-term memories by ID.

Parameters:

| Name         | Type | Description                   | Default    |
| ------------ | ---- | ----------------------------- | ---------- |
| `memory_ids` |      | List of memory IDs to delete. | *required* |
| `namespace`  |      | Optional namespace override.  | *required* |
| `user_id`    |      | Optional user ID override.    | *required* |

Returns:

| Type             | Description                                 |
| ---------------- | ------------------------------------------- |
| `dict[str, Any]` | A dictionary with status and deleted_count. |

Source code in `src/adk_redis/tools/memory/delete.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Delete long-term memories by ID.

  Args:
      memory_ids: List of memory IDs to delete.
      namespace: Optional namespace override.
      user_id: Optional user ID override.

  Returns:
      A dictionary with status and deleted_count.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  memory_ids = args.get("memory_ids", [])
  self._get_namespace(args.get("namespace"))
  self._get_user_id(args.get("user_id"))

  if not memory_ids:
    return {"status": "error", "message": "memory_ids is required"}

  try:
    # delete_long_term_memories only takes memory_ids
    client = self._get_client()
    response = await client.delete_long_term_memories(
        memory_ids=memory_ids,
    )

    # Response is AckResponse with 'status' field containing message like "ok, deleted 2 memories"
    status_msg = response.status

    # Parse the deleted count from the status message
    import re

    match = re.search(r"deleted (\d+)", status_msg)
    deleted_count = int(match.group(1)) if match else 0

    is_success = "ok" in status_msg.lower()

    return {
        "status": "success" if is_success else "error",
        "deleted_count": deleted_count,
        "message": status_msg,
    }

  except Exception as e:
    logger.error("Failed to delete memories: %s", e)
    return {
        "status": "error",
        "message": f"Failed to delete memories: {str(e)}",
    }
```

### GetMemoryTool

```python
GetMemoryTool(*, config: MemoryToolConfig | None = None, name: str = 'get_memory', description: str = 'Retrieves a specific long-term memory by its ID. Use this when you need the full details of a known memory.')
```

Bases: `BaseMemoryTool`

Tool for retrieving a specific long-term memory by ID.

This tool allows the LLM to retrieve a specific memory when it knows the memory ID. Use this when you need to access the full details of a memory that was previously found via search.

Example

```python
from adk_redis.tools.memory import GetMemoryTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
tool = GetMemoryTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Get Memory Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                                         |
| ------------- | ------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                                             |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'get_memory'`                                                                                                  |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Retrieves a specific long-term memory by its ID. Use this when you need the full details of a known memory.'` |

Source code in `src/adk_redis/tools/memory/get.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "get_memory",
    description: str = (
        "Retrieves a specific long-term memory by its ID. "
        "Use this when you need the full details of a known memory."
    ),
):
  """Initialize the Get Memory Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Retrieve a specific memory by ID.

Parameters:

| Name        | Type | Description                              | Default    |
| ----------- | ---- | ---------------------------------------- | ---------- |
| `memory_id` |      | The unique ID of the memory to retrieve. | *required* |

Returns:

| Type             | Description                                  |
| ---------------- | -------------------------------------------- |
| `dict[str, Any]` | A dictionary with status and memory details. |

Source code in `src/adk_redis/tools/memory/get.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Retrieve a specific memory by ID.

  Args:
      memory_id: The unique ID of the memory to retrieve.

  Returns:
      A dictionary with status and memory details.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  memory_id = args.get("memory_id")

  if not memory_id:
    return {"status": "error", "message": "memory_id is required"}

  try:
    client = self._get_client()
    memory = await client.get_long_term_memory(memory_id=memory_id)

    return {
        "status": "success",
        "memory": {
            "id": memory.id,
            "content": memory.text,
            "topics": memory.topics or [],
            "entities": memory.entities or [],
            "memory_type": memory.memory_type,
            "namespace": memory.namespace,
            "user_id": memory.user_id,
            "session_id": memory.session_id,
            "created_at": str(memory.created_at)
            if memory.created_at
            else None,
            "last_accessed": str(memory.last_accessed)
            if memory.last_accessed
            else None,
        },
    }

  except Exception as e:
    error_msg = str(e)
    if "not found" in error_msg.lower() or "404" in error_msg:
      return {
          "status": "error",
          "message": f"Memory with ID '{memory_id}' not found",
      }
    logger.error("Failed to get memory: %s", e)
    return {
        "status": "error",
        "message": f"Failed to get memory: {error_msg}",
    }
```

### MemoryPromptTool

```python
MemoryPromptTool(*, config: MemoryToolConfig | None = None, name: str = 'memory_prompt', description: str = 'Enriches a prompt with relevant memories from long-term storage. Use this to provide personalized context based on past interactions.')
```

Bases: `BaseMemoryTool`

Tool for enriching prompts with relevant memories.

This tool searches long-term memory for relevant context and enriches a system prompt with the retrieved memories. It's useful for providing the LLM with personalized context based on past interactions.

Example

```python
from adk_redis.tools.memory import MemoryPromptTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
tool = MemoryPromptTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Memory Prompt Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                                                                   |
| ------------- | ------------------ | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                                                                       |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'memory_prompt'`                                                                                                                         |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Enriches a prompt with relevant memories from long-term storage. Use this to provide personalized context based on past interactions.'` |

Source code in `src/adk_redis/tools/memory/prompt.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "memory_prompt",
    description: str = (
        "Enriches a prompt with relevant memories from long-term storage. "
        "Use this to provide personalized context based on past interactions."
    ),
):
  """Initialize the Memory Prompt Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Enrich a prompt with relevant memories.

Parameters:

| Name            | Type | Description                                | Default    |
| --------------- | ---- | ------------------------------------------ | ---------- |
| `query`         |      | The query to search for relevant memories. | *required* |
| `system_prompt` |      | Optional base system prompt to enrich.     | *required* |
| `namespace`     |      | Optional namespace override.               | *required* |
| `user_id`       |      | Optional user ID override.                 | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status and enriched_prompt. |

Source code in `src/adk_redis/tools/memory/prompt.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Enrich a prompt with relevant memories.

  Args:
      query: The query to search for relevant memories.
      system_prompt: Optional base system prompt to enrich.
      namespace: Optional namespace override.
      user_id: Optional user ID override.

  Returns:
      A dictionary with status and enriched_prompt.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  query = args.get("query")
  system_prompt = args.get("system_prompt", "")
  namespace = self._get_namespace(args.get("namespace"))
  user_id = self._get_user_id(args.get("user_id"))

  if not query:
    return {"status": "error", "message": "query is required"}

  try:
    # memory_prompt requires either session_id or long_term_search
    # We'll use long_term_search to search long-term memories
    long_term_search = {
        "limit": self._config.search_top_k,
    }

    client = self._get_client()
    response = await client.memory_prompt(
        query=query,
        user_id=user_id,
        namespace=namespace,
        long_term_search=long_term_search,
    )

    # Extract the enriched prompt and combine with system prompt if provided
    enriched_prompt = response.get("prompt", query)
    if system_prompt:
      enriched_prompt = f"{system_prompt}\n\n{enriched_prompt}"

    memories_used = len(response.get("memories", []))

    return {
        "status": "success",
        "enriched_prompt": enriched_prompt,
        "memories_used": memories_used,
    }

  except Exception as e:
    logger.error("Failed to enrich prompt: %s", e)
    return {
        "status": "error",
        "message": f"Failed to enrich prompt: {str(e)}",
    }
```

### MemoryToolConfig

Bases: `BaseModel`

Shared configuration for all Redis Agent Memory tools.

This configuration is used by all memory tools to connect to the Agent Memory Server and manage memory operations.

Attributes:

| Name                         | Type    | Description                                        |
| ---------------------------- | ------- | -------------------------------------------------- |
| `api_base_url`               | `str`   | Base URL of the Agent Memory Server.               |
| `timeout`                    | `float` | HTTP request timeout in seconds.                   |
| `default_namespace`          | `str`   | Default namespace for memory operations.           |
| `default_user_id`            | \`str   | None\`                                             |
| `search_top_k`               | `int`   | Default maximum number of memories to retrieve.    |
| `distance_threshold`         | \`float | None\`                                             |
| `recency_boost`              | `bool`  | Enable recency-aware re-ranking of search results. |
| `semantic_weight`            | `float` | Weight for semantic similarity (0.0-1.0).          |
| `recency_weight`             | `float` | Weight for recency score (0.0-1.0).                |
| `freshness_weight`           | `float` | Weight for freshness within recency score.         |
| `novelty_weight`             | `float` | Weight for novelty within recency score.           |
| `half_life_last_access_days` | `float` | Half-life in days for last_accessed decay.         |
| `half_life_created_days`     | `float` | Half-life in days for created_at decay.            |
| `deduplicate`                | `bool`  | Enable deduplication when creating memories.       |

Example

```python
from adk_redis.tools.memory import MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    recency_boost=True,
)
```

### SearchMemoryTool

```python
SearchMemoryTool(*, config: MemoryToolConfig | None = None, name: str = 'search_memory', description: str = 'Searches long-term memory for relevant information. Use this to recall facts, preferences, or past interactions.')
```

Bases: `BaseMemoryTool`

Tool for searching long-term memories.

This tool performs semantic search against long-term memory with optional recency boosting. Use this when the LLM needs to recall specific information from past interactions.

Example

```python
from adk_redis.tools.memory import SearchMemoryTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    recency_boost=True,
)
tool = SearchMemoryTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Search Memory Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                                              |
| ------------- | ------------------ | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                                                  |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'search_memory'`                                                                                                    |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Searches long-term memory for relevant information. Use this to recall facts, preferences, or past interactions.'` |

Source code in `src/adk_redis/tools/memory/search.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "search_memory",
    description: str = (
        "Searches long-term memory for relevant information. "
        "Use this to recall facts, preferences, or past interactions."
    ),
):
  """Initialize the Search Memory Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Search for relevant memories.

Parameters:

| Name        | Type | Description                           | Default    |
| ----------- | ---- | ------------------------------------- | ---------- |
| `query`     |      | The search query.                     | *required* |
| `limit`     |      | Maximum number of memories to return. | *required* |
| `namespace` |      | Optional namespace override.          | *required* |
| `user_id`   |      | Optional user ID override.            | *required* |

Returns:

| Type             | Description                                    |
| ---------------- | ---------------------------------------------- |
| `dict[str, Any]` | A dictionary with status and list of memories. |

Source code in `src/adk_redis/tools/memory/search.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Search for relevant memories.

  Args:
      query: The search query.
      limit: Maximum number of memories to return.
      namespace: Optional namespace override.
      user_id: Optional user ID override.

  Returns:
      A dictionary with status and list of memories.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  query = args.get("query")
  limit = args.get("limit", self._config.search_top_k)
  namespace = self._get_namespace(args.get("namespace"))
  user_id = self._get_user_id(args.get("user_id"))

  if not query:
    return {"status": "error", "message": "query is required"}

  try:
    # Use search_long_term_memory which supports namespace filtering
    client = self._get_client()
    from agent_memory_client.filters import Namespace
    from agent_memory_client.filters import UserId

    ns = Namespace(eq=namespace)
    uid = UserId(eq=user_id) if user_id else None
    response = await client.search_long_term_memory(
        text=query,
        namespace=ns,
        user_id=uid,
        distance_threshold=self._config.distance_threshold,
        limit=limit,
    )

    # Response is a MemoryRecordResults object with .memories attribute
    memories = []
    for memory in response.memories:
      memories.append(
          {
              "id": memory.id,
              "content": memory.text,
              "score": getattr(memory, "dist", 0.0),
              "topics": memory.topics or [],
              "memory_type": memory.memory_type,
              "created_at": str(memory.created_at)
              if memory.created_at
              else None,
          }
      )

    return {
        "status": "success",
        "memories": memories,
        "count": len(memories),
    }

  except Exception as e:
    logger.error("Failed to search memories: %s", e)
    return {
        "status": "error",
        "message": f"Failed to search memories: {str(e)}",
    }
```

### UpdateMemoryTool

```python
UpdateMemoryTool(*, config: MemoryToolConfig | None = None, name: str = 'update_memory', description: str = 'Updates an existing long-term memory. Use this when the user asks to modify or correct stored information.')
```

Bases: `BaseMemoryTool`

Tool for updating existing long-term memories.

This tool allows the LLM to modify the content or metadata of existing memories. Use this when the user asks to update or correct previously stored information.

Example

```python
from adk_redis.tools.memory import UpdateMemoryTool, MemoryToolConfig

config = MemoryToolConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
tool = UpdateMemoryTool(config=config)

# Use with ADK agent
agent = Agent(
    name="my_agent",
    tools=[tool],
)
```

Initialize the Update Memory Tool.

Parameters:

| Name          | Type               | Description                                   | Default                                                                                                        |
| ------------- | ------------------ | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `config`      | \`MemoryToolConfig | None\`                                        | Configuration for the tool. If None, uses defaults.                                                            |
| `name`        | `str`              | The name of the tool (exposed to LLM).        | `'update_memory'`                                                                                              |
| `description` | `str`              | The description of the tool (exposed to LLM). | `'Updates an existing long-term memory. Use this when the user asks to modify or correct stored information.'` |

Source code in `src/adk_redis/tools/memory/update.py`

```python
def __init__(
    self,
    *,
    config: MemoryToolConfig | None = None,
    name: str = "update_memory",
    description: str = (
        "Updates an existing long-term memory. "
        "Use this when the user asks to modify or correct stored information."
    ),
):
  """Initialize the Update Memory Tool.

  Args:
      config: Configuration for the tool. If None, uses defaults.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      config=config or MemoryToolConfig(),
      name=name,
      description=description,
  )
```

#### run_async

```python
run_async(**kwargs: Any) -> dict[str, Any]
```

Update an existing long-term memory.

Parameters:

| Name        | Type | Description                     | Default    |
| ----------- | ---- | ------------------------------- | ---------- |
| `memory_id` |      | The ID of the memory to update. | *required* |
| `content`   |      | New content for the memory.     | *required* |
| `topics`    |      | New list of topics/tags.        | *required* |
| `namespace` |      | Optional namespace override.    | *required* |
| `user_id`   |      | Optional user ID override.      | *required* |

Returns:

| Type             | Description                                       |
| ---------------- | ------------------------------------------------- |
| `dict[str, Any]` | A dictionary with status and updated memory info. |

Source code in `src/adk_redis/tools/memory/update.py`

```python
async def run_async(self, **kwargs: Any) -> dict[str, Any]:
  """Update an existing long-term memory.

  Args:
      memory_id: The ID of the memory to update.
      content: New content for the memory.
      topics: New list of topics/tags.
      namespace: Optional namespace override.
      user_id: Optional user ID override.

  Returns:
      A dictionary with status and updated memory info.
  """
  # ADK passes parameters in kwargs['args']
  args = kwargs.get("args", kwargs)

  memory_id = args.get("memory_id")
  content = args.get("content")
  topics = args.get("topics")
  self._get_namespace(args.get("namespace"))
  self._get_user_id(args.get("user_id"))

  if not memory_id:
    return {"status": "error", "message": "memory_id is required"}

  if not content and not topics:
    return {
        "status": "error",
        "message": "At least one of content or topics must be provided",
    }

  try:
    # Build updates dict - use 'text' instead of 'content'
    updates = {}
    if content:
      updates["text"] = content
    if topics is not None:
      updates["topics"] = topics

    # edit_long_term_memory only takes memory_id and updates dict
    client = self._get_client()
    response = await client.edit_long_term_memory(
        memory_id=memory_id,
        updates=updates,
    )

    return {
        "status": "success",
        "memory_id": response.id,
        "message": f"Memory {response.id} updated successfully",
    }

  except Exception as e:
    logger.error("Failed to update memory: %s", e)
    return {
        "status": "error",
        "message": f"Failed to update memory: {str(e)}",
    }
```

### BaseRedisSearchTool

```python
BaseRedisSearchTool(*, name: str, description: str, index: SearchIndex | AsyncSearchIndex, return_fields: list[str] | None = None)
```

Bases: `BaseTool`

Base class for ALL Redis search tools using RedisVL.

This class provides common functionality shared by all Redis search tools:

- Index management (sync and async)
- Query execution with proper async handling
- Standard response formatting
- Error handling

Subclasses should use `_run_search` to execute queries with consistent error handling and response formatting.

Initialize the base Redis search tool.

Parameters:

| Name            | Type          | Description                                   | Default                                               |
| --------------- | ------------- | --------------------------------------------- | ----------------------------------------------------- |
| `name`          | `str`         | The name of the tool (exposed to LLM).        | *required*                                            |
| `description`   | `str`         | The description of the tool (exposed to LLM). | *required*                                            |
| `index`         | \`SearchIndex | AsyncSearchIndex\`                            | The RedisVL SearchIndex or AsyncSearchIndex to query. |
| `return_fields` | \`list[str]   | None\`                                        | Optional list of fields to return in results.         |

Source code in `src/adk_redis/tools/search/_base.py`

```python
def __init__(
    self,
    *,
    name: str,
    description: str,
    index: SearchIndex | AsyncSearchIndex,
    return_fields: list[str] | None = None,
):
  """Initialize the base Redis search tool.

  Args:
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      return_fields: Optional list of fields to return in results.
  """
  super().__init__(name=name, description=description)
  self._index = index
  self._return_fields = return_fields
  self._is_async_index = isinstance(index, AsyncSearchIndex)
```

### RedisAggregatedHybridQueryConfig

Bases: `BaseModel`

Configuration for aggregated (client-side) Redis hybrid search queries.

.. deprecated:: This config is for older Redis/RedisVL versions. For newer setups (RedisVL >= 0.13.0, Redis >= 8.4.0), prefer RedisHybridQueryConfig which uses native server-side hybrid search for better performance.

This config uses AggregateHybridQuery which performs client-side hybrid search using FT.AGGREGATE with weighted score combination. It works with any Redis version that has RediSearch installed.

Recommended for

- Redis < 8.4.0
- RedisVL < 0.13.0
- Environments where native FT.HYBRID is not available

Example

```python
from adk_redis import (
    RedisHybridSearchTool,
    RedisAggregatedHybridQueryConfig,
)

config = RedisAggregatedHybridQueryConfig(
    text_field_name="content",
    alpha=0.7,  # 70% text, 30% vector
)
tool = RedisHybridSearchTool(index=index, vectorizer=vectorizer, config=config)
```

Attributes:

| Name                | Type               | Description                                                                                                                                                        |
| ------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `text_field_name`   | `str`              | Name of the text field for BM25 search.                                                                                                                            |
| `vector_field_name` | `str`              | Name of the vector field for similarity search.                                                                                                                    |
| `text_scorer`       | `str`              | Text scoring algorithm (default: "BM25STD").                                                                                                                       |
| `alpha`             | `float`            | Weight for text score (default: 0.7). Higher values favor text matching over vector similarity. Combined score is: alpha * text_score + (1 - alpha) * vector_score |
| `num_results`       | `int`              | Number of results to return.                                                                                                                                       |
| `dtype`             | `str`              | Data type of the vector.                                                                                                                                           |
| `stopwords`         | \`str              | set[str]                                                                                                                                                           |
| `dialect`           | `int`              | RediSearch query dialect version.                                                                                                                                  |
| `text_weights`      | \`dict[str, float] | None\`                                                                                                                                                             |

#### to_query_kwargs

```python
to_query_kwargs(text: str, vector: list[float], return_fields: list[str] | None = None, filter_expression: Any | None = None) -> dict[str, Any]
```

Convert config to AggregateHybridQuery kwargs.

Parameters:

| Name                | Type          | Description                       | Default                              |
| ------------------- | ------------- | --------------------------------- | ------------------------------------ |
| `text`              | `str`         | The query text for BM25 matching. | *required*                           |
| `vector`            | `list[float]` | The query vector embedding.       | *required*                           |
| `return_fields`     | \`list[str]   | None\`                            | Optional list of fields to return.   |
| `filter_expression` | \`Any         | None\`                            | Optional filter expression to apply. |

Returns:

| Type             | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `dict[str, Any]` | Dictionary of kwargs suitable for AggregateHybridQuery constructor. |

Source code in `src/adk_redis/tools/search/_config.py`

```python
def to_query_kwargs(
    self,
    text: str,
    vector: list[float],
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
) -> dict[str, Any]:
  """Convert config to AggregateHybridQuery kwargs.

  Args:
      text: The query text for BM25 matching.
      vector: The query vector embedding.
      return_fields: Optional list of fields to return.
      filter_expression: Optional filter expression to apply.

  Returns:
      Dictionary of kwargs suitable for AggregateHybridQuery constructor.
  """
  return {
      "text": text,
      "text_field_name": self.text_field_name,
      "vector": vector,
      "vector_field_name": self.vector_field_name,
      "text_scorer": self.text_scorer,
      "alpha": self.alpha,
      "dtype": self.dtype,
      "num_results": self.num_results,
      "return_fields": return_fields,
      "stopwords": self.stopwords,
      "dialect": self.dialect,
      "text_weights": self.text_weights,
      "filter_expression": filter_expression,
  }
```

### RedisHybridQueryConfig

Bases: `BaseModel`

Configuration for native Redis hybrid search queries.

Uses Redis's native FT.HYBRID command for server-side hybrid search combining semantic vector similarity with keyword-based BM25 text matching.

Requirements

- RedisVL >= 0.13.0
- Redis >= 8.4.0
- redis-py >= 7.1.0

For older Redis/RedisVL versions, use RedisAggregatedHybridQueryConfig instead.

Example

```python
from adk_redis import (
    RedisHybridSearchTool,
    RedisHybridQueryConfig,
)

config = RedisHybridQueryConfig(
    text_field_name="content",
    combination_method="LINEAR",
    linear_alpha=0.7,  # 70% text, 30% vector
)
tool = RedisHybridSearchTool(index=index, vectorizer=vectorizer, config=config)
```

Attributes:

| Name                      | Type               | Description                                         |
| ------------------------- | ------------------ | --------------------------------------------------- |
| `text_field_name`         | `str`              | Name of the text field for BM25 search.             |
| `vector_field_name`       | `str`              | Name of the vector field for similarity search.     |
| `vector_param_name`       | `str`              | Name of the parameter substitution for vector blob. |
| `text_scorer`             | `str`              | Text scoring algorithm (default: "BM25STD").        |
| `yield_text_score_as`     | \`str              | None\`                                              |
| `vector_search_method`    | \`str              | None\`                                              |
| `knn_ef_runtime`          | `int`              | Exploration factor for HNSW when using KNN.         |
| `range_radius`            | \`float            | None\`                                              |
| `range_epsilon`           | `float`            | Epsilon for RANGE search accuracy.                  |
| `yield_vsim_score_as`     | \`str              | None\`                                              |
| `combination_method`      | \`str              | None\`                                              |
| `linear_alpha`            | `float`            | Weight of text score when using LINEAR (0.0-1.0).   |
| `rrf_window`              | `int`              | Window size for RRF combination.                    |
| `rrf_constant`            | `int`              | Constant for RRF combination.                       |
| `yield_combined_score_as` | \`str              | None\`                                              |
| `num_results`             | `int`              | Number of results to return.                        |
| `dtype`                   | `str`              | Data type of the vector.                            |
| `stopwords`               | \`str              | set[str]                                            |
| `text_weights`            | \`dict[str, float] | None\`                                              |

#### to_query_kwargs

```python
to_query_kwargs(text: str, vector: list[float], return_fields: list[str] | None = None, filter_expression: Any | None = None) -> dict[str, Any]
```

Convert config to native HybridQuery kwargs.

Parameters:

| Name                | Type          | Description                       | Default                              |
| ------------------- | ------------- | --------------------------------- | ------------------------------------ |
| `text`              | `str`         | The query text for BM25 matching. | *required*                           |
| `vector`            | `list[float]` | The query vector embedding.       | *required*                           |
| `return_fields`     | \`list[str]   | None\`                            | Optional list of fields to return.   |
| `filter_expression` | \`Any         | None\`                            | Optional filter expression to apply. |

Returns:

| Type             | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| `dict[str, Any]` | Dictionary of kwargs suitable for HybridQuery constructor. |

Source code in `src/adk_redis/tools/search/_config.py`

```python
def to_query_kwargs(
    self,
    text: str,
    vector: list[float],
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
) -> dict[str, Any]:
  """Convert config to native HybridQuery kwargs.

  Args:
      text: The query text for BM25 matching.
      vector: The query vector embedding.
      return_fields: Optional list of fields to return.
      filter_expression: Optional filter expression to apply.

  Returns:
      Dictionary of kwargs suitable for HybridQuery constructor.
  """
  return {
      "text": text,
      "text_field_name": self.text_field_name,
      "vector": vector,
      "vector_field_name": self.vector_field_name,
      "vector_param_name": self.vector_param_name,
      "text_scorer": self.text_scorer,
      "yield_text_score_as": self.yield_text_score_as,
      "vector_search_method": self.vector_search_method,
      "knn_ef_runtime": self.knn_ef_runtime,
      "range_radius": self.range_radius,
      "range_epsilon": self.range_epsilon,
      "yield_vsim_score_as": self.yield_vsim_score_as,
      "filter_expression": filter_expression,
      "combination_method": self.combination_method,
      "rrf_window": self.rrf_window,
      "rrf_constant": self.rrf_constant,
      "linear_alpha": self.linear_alpha,
      "yield_combined_score_as": self.yield_combined_score_as,
      "dtype": self.dtype,
      "num_results": self.num_results,
      "return_fields": return_fields,
      "stopwords": self.stopwords,
      "text_weights": self.text_weights,
  }
```

### RedisHybridSearchTool

```python
RedisHybridSearchTool(*, index: SearchIndex | AsyncSearchIndex, vectorizer: BaseVectorizer, config: RedisHybridQueryConfig | RedisAggregatedHybridQueryConfig | None = None, return_fields: list[str] | None = None, filter_expression: Any | None = None, name: str = 'redis_hybrid_search', description: str = 'Search using both semantic similarity and keyword matching.')
```

Bases: `VectorizedSearchTool`

Hybrid search tool combining vector similarity and BM25 text search.

This tool performs a hybrid search that combines semantic vector similarity with keyword-based BM25 text matching. It automatically detects the installed RedisVL version and uses the appropriate implementation:

- **RedisVL >= 0.13.0**: Uses native FT.HYBRID command (server-side fusion) with RedisHybridQueryConfig. Requires Redis >= 8.4.0.
- **RedisVL < 0.13.0**: Uses AggregateHybridQuery (client-side fusion) with RedisAggregatedHybridQueryConfig. Works with any Redis version.

Example (native mode - RedisVL >= 0.13.0):

```python
from adk_redis import (
    RedisHybridSearchTool,
    RedisHybridQueryConfig,
)

config = RedisHybridQueryConfig(
    text_field_name="content",
    combination_method="LINEAR",
    linear_alpha=0.7,  # 70% text, 30% vector
)
tool = RedisHybridSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=config,
)
```

Example (aggregate mode - older versions):

```python
from adk_redis import (
    RedisHybridSearchTool,
    RedisAggregatedHybridQueryConfig,
)

config = RedisAggregatedHybridQueryConfig(
    text_field_name="content",
    alpha=0.7,  # 70% text, 30% vector
)
tool = RedisHybridSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=config,
)
```

Initialize the hybrid search tool.

Parameters:

| Name                | Type                     | Description                                   | Default                                                         |
| ------------------- | ------------------------ | --------------------------------------------- | --------------------------------------------------------------- |
| `index`             | \`SearchIndex            | AsyncSearchIndex\`                            | The RedisVL SearchIndex or AsyncSearchIndex to query.           |
| `vectorizer`        | `BaseVectorizer`         | The vectorizer for embedding queries.         | *required*                                                      |
| `config`            | \`RedisHybridQueryConfig | RedisAggregatedHybridQueryConfig              | None\`                                                          |
| `return_fields`     | \`list[str]              | None\`                                        | Optional list of fields to return in results.                   |
| `filter_expression` | \`Any                    | None\`                                        | Optional filter expression to narrow results.                   |
| `name`              | `str`                    | The name of the tool (exposed to LLM).        | `'redis_hybrid_search'`                                         |
| `description`       | `str`                    | The description of the tool (exposed to LLM). | `'Search using both semantic similarity and keyword matching.'` |

Raises:

| Type         | Description                                              |
| ------------ | -------------------------------------------------------- |
| `ValueError` | If RedisHybridQueryConfig is used with RedisVL < 0.13.0. |

Warns:

| Type                 | Description                                                                                      |
| -------------------- | ------------------------------------------------------------------------------------------------ |
| `DeprecationWarning` | If RedisAggregatedHybridQueryConfig is used when native hybrid is available (RedisVL >= 0.13.0). |

Source code in `src/adk_redis/tools/search/hybrid.py`

```python
def __init__(
    self,
    *,
    index: SearchIndex | AsyncSearchIndex,
    vectorizer: BaseVectorizer,
    config: (
        RedisHybridQueryConfig | RedisAggregatedHybridQueryConfig | None
    ) = None,
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
    name: str = "redis_hybrid_search",
    description: str = "Search using both semantic similarity and keyword matching.",
):
  """Initialize the hybrid search tool.

  Args:
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      vectorizer: The vectorizer for embedding queries.
      config: Configuration for query parameters. Can be either:
          - RedisHybridQueryConfig: For native FT.HYBRID (RedisVL >= 0.13.0)
          - RedisAggregatedHybridQueryConfig: For client-side hybrid (older)
          If None, auto-detects based on installed RedisVL version.
      return_fields: Optional list of fields to return in results.
      filter_expression: Optional filter expression to narrow results.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).

  Raises:
      ValueError: If RedisHybridQueryConfig is used with RedisVL < 0.13.0.

  Warns:
      DeprecationWarning: If RedisAggregatedHybridQueryConfig is used when
          native hybrid is available (RedisVL >= 0.13.0).
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      vectorizer=vectorizer,
      return_fields=return_fields,
  )

  self._supports_native = _supports_native_hybrid(index)

  # Auto-detect config if not provided
  if config is None:
    if self._supports_native:
      config = RedisHybridQueryConfig()
    else:
      config = RedisAggregatedHybridQueryConfig()

  # Validate config compatibility with installed version
  self._use_native = isinstance(config, RedisHybridQueryConfig)

  if self._use_native and not self._supports_native:
    raise ValueError(
        "RedisHybridQueryConfig requires RedisVL >= 0.13.0 and Redis >= "
        f"8.4.0. Installed RedisVL version: {_get_redisvl_version()}, "
        f"Redis server version: {_get_redis_server_version(index)}. "
        "Use RedisAggregatedHybridQueryConfig for older versions."
    )

  if not self._use_native and self._supports_native:
    warnings.warn(
        "RedisAggregatedHybridQueryConfig is deprecated for RedisVL >="
        " 0.13.0. Consider using RedisHybridQueryConfig for native FT.HYBRID"
        " support with better performance. RedisAggregatedHybridQueryConfig"
        " will continue to work but uses client-side score combination.",
        DeprecationWarning,
        stacklevel=2,
    )

  self._config = config
  self._filter_expression = filter_expression
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the vector-based search query.

Parameters:

| Name           | Type             | Description                                   | Default    |
| -------------- | ---------------- | --------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM, must include 'query'. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                   | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status, count, and results. |

Source code in `src/adk_redis/tools/search/_base.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the vector-based search query.

  Args:
      args: Arguments from the LLM, must include 'query'.
      tool_context: The tool execution context.

  Returns:
      A dictionary with status, count, and results.
  """

  async def build_query_fn(query_text: str, args: dict[str, Any]) -> Any:
    embedding = await self._vectorizer.aembed(query_text)
    return self._build_query(query_text, embedding, **args)

  return await self._run_search(args, build_query_fn)
```

### RedisRangeQueryConfig

Bases: `BaseModel`

Configuration for Redis vector range search queries.

Range search finds all documents within a specified distance threshold from the query vector, rather than returning a fixed number of results.

Attributes:

| Name                        | Type       | Description                                    |
| --------------------------- | ---------- | ---------------------------------------------- |
| `vector_field_name`         | `str`      | Name of the vector field in the index.         |
| `distance_threshold`        | `float`    | Maximum distance for results (default: 0.2).   |
| `num_results`               | `int`      | Maximum number of results to return.           |
| `dtype`                     | `str`      | Data type of the vector (default: "float32").  |
| `return_score`              | `bool`     | Whether to return vector distance scores.      |
| `dialect`                   | `int`      | RediSearch query dialect version.              |
| `sort_by`                   | `SortSpec` | Field(s) to order results by.                  |
| `in_order`                  | `bool`     | Require query terms in same order as document. |
| `normalize_vector_distance` | `bool`     | Convert distance to 0-1 similarity score.      |
| `epsilon`                   | \`float    | None\`                                         |

#### to_query_kwargs

```python
to_query_kwargs(vector: list[float], filter_expression: Any | None = None) -> dict[str, Any]
```

Convert config to VectorRangeQuery kwargs.

Parameters:

| Name                | Type          | Description                 | Default                              |
| ------------------- | ------------- | --------------------------- | ------------------------------------ |
| `vector`            | `list[float]` | The query vector embedding. | *required*                           |
| `filter_expression` | \`Any         | None\`                      | Optional filter expression to apply. |

Returns:

| Type             | Description                                                     |
| ---------------- | --------------------------------------------------------------- |
| `dict[str, Any]` | Dictionary of kwargs suitable for VectorRangeQuery constructor. |

Source code in `src/adk_redis/tools/search/_config.py`

```python
def to_query_kwargs(
    self, vector: list[float], filter_expression: Any | None = None
) -> dict[str, Any]:
  """Convert config to VectorRangeQuery kwargs.

  Args:
      vector: The query vector embedding.
      filter_expression: Optional filter expression to apply.

  Returns:
      Dictionary of kwargs suitable for VectorRangeQuery constructor.
  """
  kwargs: dict[str, Any] = {
      "vector": vector,
      "vector_field_name": self.vector_field_name,
      "distance_threshold": self.distance_threshold,
      "num_results": self.num_results,
      "dtype": self.dtype,
      "return_score": self.return_score,
      "dialect": self.dialect,
      "sort_by": self.sort_by,
      "in_order": self.in_order,
      "normalize_vector_distance": self.normalize_vector_distance,
      "filter_expression": filter_expression,
  }

  # Version-dependent: only include if not None
  if self.epsilon is not None:
    kwargs["epsilon"] = self.epsilon

  return kwargs
```

### RedisRangeSearchTool

```python
RedisRangeSearchTool(*, index: SearchIndex | AsyncSearchIndex, vectorizer: BaseVectorizer, config: RedisRangeQueryConfig | None = None, return_fields: list[str] | None = None, filter_expression: Any | None = None, name: str = 'redis_range_search', description: str = 'Find all documents within a similarity threshold.')
```

Bases: `VectorizedSearchTool`

Vector range search tool using distance threshold.

This tool finds all documents within a specified distance threshold from the query vector. Unlike KNN search which returns a fixed number of results, range search returns all documents that are "close enough" based on the threshold.

Example

```python
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer
from adk_redis import (
    RedisRangeSearchTool,
    RedisRangeQueryConfig,
)

index = SearchIndex.from_yaml("schema.yaml")
vectorizer = HFTextVectorizer(model="redis/langcache-embed-v2")

# Using config object (recommended)
config = RedisRangeQueryConfig(
    distance_threshold=0.3,  # Only return docs within 0.3 distance
)
tool = RedisRangeSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=config,
    return_fields=["title", "content"],
)

agent = Agent(model="gemini-2.5-flash", tools=[tool])
```

Initialize the range search tool.

Parameters:

| Name                | Type                    | Description                                   | Default                                                                                                                                                                   |
| ------------------- | ----------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index`             | \`SearchIndex           | AsyncSearchIndex\`                            | The RedisVL SearchIndex or AsyncSearchIndex to query.                                                                                                                     |
| `vectorizer`        | `BaseVectorizer`        | The vectorizer for embedding queries.         | *required*                                                                                                                                                                |
| `config`            | \`RedisRangeQueryConfig | None\`                                        | Configuration for query parameters. If None, uses defaults. See RedisRangeQueryConfig for available options including distance_threshold, vector_field_name, and epsilon. |
| `return_fields`     | \`list[str]             | None\`                                        | Optional list of fields to return in results.                                                                                                                             |
| `filter_expression` | \`Any                   | None\`                                        | Optional filter expression to narrow results.                                                                                                                             |
| `name`              | `str`                   | The name of the tool (exposed to LLM).        | `'redis_range_search'`                                                                                                                                                    |
| `description`       | `str`                   | The description of the tool (exposed to LLM). | `'Find all documents within a similarity threshold.'`                                                                                                                     |

Source code in `src/adk_redis/tools/search/range.py`

```python
def __init__(
    self,
    *,
    index: SearchIndex | AsyncSearchIndex,
    vectorizer: BaseVectorizer,
    config: RedisRangeQueryConfig | None = None,
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
    name: str = "redis_range_search",
    description: str = "Find all documents within a similarity threshold.",
):
  """Initialize the range search tool.

  Args:
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      vectorizer: The vectorizer for embedding queries.
      config: Configuration for query parameters. If None, uses defaults.
          See RedisRangeQueryConfig for available options including
          distance_threshold, vector_field_name, and epsilon.
      return_fields: Optional list of fields to return in results.
      filter_expression: Optional filter expression to narrow results.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      vectorizer=vectorizer,
      return_fields=return_fields,
  )
  self._config = config or RedisRangeQueryConfig()
  self._filter_expression = filter_expression
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the vector-based search query.

Parameters:

| Name           | Type             | Description                                   | Default    |
| -------------- | ---------------- | --------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM, must include 'query'. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                   | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status, count, and results. |

Source code in `src/adk_redis/tools/search/_base.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the vector-based search query.

  Args:
      args: Arguments from the LLM, must include 'query'.
      tool_context: The tool execution context.

  Returns:
      A dictionary with status, count, and results.
  """

  async def build_query_fn(query_text: str, args: dict[str, Any]) -> Any:
    embedding = await self._vectorizer.aembed(query_text)
    return self._build_query(query_text, embedding, **args)

  return await self._run_search(args, build_query_fn)
```

### RedisSQLSearchTool

```python
RedisSQLSearchTool(*, index: SearchIndex | AsyncSearchIndex, sql_redis_options: dict[str, Any] | None = None, return_fields: list[str] | None = None, name: str = 'redis_sql_search', description: str = _DEFAULT_DESCRIPTION)
```

Bases: `BaseRedisSearchTool`

Search tool that lets the LLM issue SQL SELECT statements.

Wraps `redisvl.query.SQLQuery`, which translates SQL into Redis `FT.SEARCH` / `FT.AGGREGATE` commands via the optional `sql-redis` extra. Use this when an agent benefits from expressing filters and projections directly in SQL rather than configuring query parameters field by field.

Example

```python
from redisvl.index import SearchIndex
from adk_redis import RedisSQLSearchTool

index = SearchIndex.from_yaml("schema.yaml")
tool = RedisSQLSearchTool(index=index)

agent = Agent(model="gemini-2.5-flash", tools=[tool])
```

Note

Requires the `sql-redis` optional dependency. Install with `pip install 'adk-redis[sql]'`.

Initialize the SQL search tool.

Parameters:

| Name                | Type             | Description                                   | Default                                                                                                                                                                                |
| ------------------- | ---------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index`             | \`SearchIndex    | AsyncSearchIndex\`                            | The RedisVL SearchIndex or AsyncSearchIndex to query.                                                                                                                                  |
| `sql_redis_options` | \`dict[str, Any] | None\`                                        | Optional passthrough options forwarded to the sql-redis executor. For example, {"schema_cache_strategy": "load_all"} eagerly loads index schemas. The redisvl default is lazy loading. |
| `return_fields`     | \`list[str]      | None\`                                        | Ignored. SQL SELECT clauses already specify the projection. Accepted for API symmetry with sibling tools.                                                                              |
| `name`              | `str`            | The name of the tool (exposed to LLM).        | `'redis_sql_search'`                                                                                                                                                                   |
| `description`       | `str`            | The description of the tool (exposed to LLM). | `_DEFAULT_DESCRIPTION`                                                                                                                                                                 |

Source code in `src/adk_redis/tools/search/sql.py`

```python
def __init__(
    self,
    *,
    index: SearchIndex | AsyncSearchIndex,
    sql_redis_options: dict[str, Any] | None = None,
    return_fields: list[str] | None = None,
    name: str = "redis_sql_search",
    description: str = _DEFAULT_DESCRIPTION,
):
  """Initialize the SQL search tool.

  Args:
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      sql_redis_options: Optional passthrough options forwarded to the
          sql-redis executor. For example, ``{"schema_cache_strategy":
          "load_all"}`` eagerly loads index schemas. The redisvl default
          is lazy loading.
      return_fields: Ignored. SQL SELECT clauses already specify the
          projection. Accepted for API symmetry with sibling tools.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      return_fields=return_fields,
  )
  self._sql_redis_options = sql_redis_options or {}
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the SQL query.

Parameters:

| Name           | Type             | Description                                                   | Default    |
| -------------- | ---------------- | ------------------------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM. Must include sql. May include params. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                                   | *required* |

Returns:

| Type             | Description                                            |
| ---------------- | ------------------------------------------------------ |
| `dict[str, Any]` | Dictionary with status, count, and results (or error). |

Source code in `src/adk_redis/tools/search/sql.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the SQL query.

  Args:
      args: Arguments from the LLM. Must include ``sql``. May include
          ``params``.
      tool_context: The tool execution context.

  Returns:
      Dictionary with status, count, and results (or error).
  """
  sql_text = args.get("sql", "")
  if not sql_text:
    return {"status": "error", "error": "SQL statement is required."}

  try:
    query = SQLQuery(
        sql=sql_text,
        params=args.get("params"),
        sql_redis_options=self._sql_redis_options or None,
    )
    results = await self._execute_query(query)
    return {
        "status": "success",
        "count": len(results),
        "results": results,
    }
  except Exception as e:  # noqa: BLE001
    return {"status": "error", "error": str(e)}
```

### RedisTextQueryConfig

Bases: `BaseModel`

Configuration for Redis full-text search queries.

This config groups all query-specific parameters for TextQuery, using BM25 scoring for keyword-based search.

Attributes:

| Name              | Type       | Description                                    |
| ----------------- | ---------- | ---------------------------------------------- |
| `text_field_name` | `str`      | Name of the text field to search.              |
| `text_scorer`     | `str`      | Text scoring algorithm (default: "BM25STD").   |
| `num_results`     | `int`      | Number of results to return (default: 10).     |
| `return_score`    | `bool`     | Whether to return the text score.              |
| `dialect`         | `int`      | RediSearch query dialect version.              |
| `sort_by`         | `SortSpec` | Field(s) to order results by.                  |
| `in_order`        | `bool`     | Require query terms in same order as document. |
| `stopwords`       | \`str      | set[str]                                       |

#### to_query_kwargs

```python
to_query_kwargs(text: str, return_fields: list[str] | None = None, filter_expression: Any | None = None) -> dict[str, Any]
```

Convert config to TextQuery kwargs.

Parameters:

| Name                | Type        | Description                       | Default                              |
| ------------------- | ----------- | --------------------------------- | ------------------------------------ |
| `text`              | `str`       | The query text for BM25 matching. | *required*                           |
| `return_fields`     | \`list[str] | None\`                            | Optional list of fields to return.   |
| `filter_expression` | \`Any       | None\`                            | Optional filter expression to apply. |

Returns:

| Type             | Description                                              |
| ---------------- | -------------------------------------------------------- |
| `dict[str, Any]` | Dictionary of kwargs suitable for TextQuery constructor. |

Source code in `src/adk_redis/tools/search/_config.py`

```python
def to_query_kwargs(
    self,
    text: str,
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
) -> dict[str, Any]:
  """Convert config to TextQuery kwargs.

  Args:
      text: The query text for BM25 matching.
      return_fields: Optional list of fields to return.
      filter_expression: Optional filter expression to apply.

  Returns:
      Dictionary of kwargs suitable for TextQuery constructor.
  """
  return {
      "text": text,
      "text_field_name": self.text_field_name,
      "text_scorer": self.text_scorer,
      "num_results": self.num_results,
      "return_score": self.return_score,
      "dialect": self.dialect,
      "sort_by": self.sort_by,
      "in_order": self.in_order,
      "stopwords": self.stopwords,
      "return_fields": return_fields,
      "filter_expression": filter_expression,
  }
```

### RedisTextSearchTool

```python
RedisTextSearchTool(*, index: SearchIndex | AsyncSearchIndex, config: RedisTextQueryConfig | None = None, return_fields: list[str] | None = None, filter_expression: Any | None = None, name: str = 'redis_text_search', description: str = 'Search for documents using keyword matching.')
```

Bases: `BaseRedisSearchTool`

Full-text search tool using BM25 scoring.

This tool performs keyword-based full-text search using BM25 scoring. Unlike vector search, it doesn't require embeddings - it matches documents based on keyword relevance.

Example

```python
from redisvl.index import SearchIndex
from adk_redis import (
    RedisTextSearchTool,
    RedisTextQueryConfig,
)

index = SearchIndex.from_yaml("schema.yaml")

# Using config object (recommended)
config = RedisTextQueryConfig(
    text_field_name="content",
    num_results=10,
    text_scorer="BM25STD",
)
tool = RedisTextSearchTool(
    index=index,
    config=config,
    return_fields=["title", "content"],
)

agent = Agent(model="gemini-2.5-flash", tools=[tool])
```

Initialize the text search tool.

Parameters:

| Name                | Type                   | Description                                   | Default                                                                          |
| ------------------- | ---------------------- | --------------------------------------------- | -------------------------------------------------------------------------------- |
| `index`             | \`SearchIndex          | AsyncSearchIndex\`                            | The RedisVL SearchIndex or AsyncSearchIndex to query.                            |
| `config`            | \`RedisTextQueryConfig | None\`                                        | Configuration for text query parameters. If not provided, defaults will be used. |
| `return_fields`     | \`list[str]            | None\`                                        | Optional list of fields to return in results.                                    |
| `filter_expression` | \`Any                  | None\`                                        | Optional filter expression to narrow results.                                    |
| `name`              | `str`                  | The name of the tool (exposed to LLM).        | `'redis_text_search'`                                                            |
| `description`       | `str`                  | The description of the tool (exposed to LLM). | `'Search for documents using keyword matching.'`                                 |

Source code in `src/adk_redis/tools/search/text.py`

```python
def __init__(
    self,
    *,
    index: SearchIndex | AsyncSearchIndex,
    config: RedisTextQueryConfig | None = None,
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
    name: str = "redis_text_search",
    description: str = "Search for documents using keyword matching.",
):
  """Initialize the text search tool.

  Args:
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      config: Configuration for text query parameters. If not provided,
          defaults will be used.
      return_fields: Optional list of fields to return in results.
      filter_expression: Optional filter expression to narrow results.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      return_fields=return_fields,
  )
  self._config = config or RedisTextQueryConfig()
  self._filter_expression = filter_expression
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the text search query.

Parameters:

| Name           | Type             | Description                                   | Default    |
| -------------- | ---------------- | --------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM, must include 'query'. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                   | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status, count, and results. |

Source code in `src/adk_redis/tools/search/text.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the text search query.

  Args:
      args: Arguments from the LLM, must include 'query'.
      tool_context: The tool execution context.

  Returns:
      A dictionary with status, count, and results.
  """

  async def build_query_fn(
      query_text: str, args: dict[str, Any]
  ) -> TextQuery:
    # Get query kwargs from config
    query_kwargs = self._config.to_query_kwargs(
        text=query_text,
        return_fields=self._return_fields,
        filter_expression=self._filter_expression,
    )
    # Allow LLM to override num_results
    if "num_results" in args:
      query_kwargs["num_results"] = args["num_results"]
    return TextQuery(**query_kwargs)

  return await self._run_search(args, build_query_fn)
```

### RedisVectorQueryConfig

Bases: `BaseModel`

Configuration for Redis vector similarity search queries.

This config groups all query-specific parameters for VectorQuery, separating them from tool-level concerns like index and vectorizer.

Attributes:

| Name                        | Type       | Description                                    |
| --------------------------- | ---------- | ---------------------------------------------- |
| `vector_field_name`         | `str`      | Name of the vector field in the index.         |
| `num_results`               | `int`      | Number of results to return (default: 10).     |
| `dtype`                     | `str`      | Data type of the vector (default: "float32").  |
| `return_score`              | `bool`     | Whether to return vector distance scores.      |
| `dialect`                   | `int`      | RediSearch query dialect version.              |
| `sort_by`                   | `SortSpec` | Field(s) to order results by.                  |
| `in_order`                  | `bool`     | Require query terms in same order as document. |
| `normalize_vector_distance` | `bool`     | Convert distance to 0-1 similarity score.      |
| `hybrid_policy`             | \`str      | None\`                                         |
| `batch_size`                | \`int      | None\`                                         |
| `ef_runtime`                | \`int      | None\`                                         |
| `search_window_size`        | \`int      | None\`                                         |
| `use_search_history`        | \`str      | None\`                                         |
| `search_buffer_capacity`    | \`int      | None\`                                         |

#### to_query_kwargs

```python
to_query_kwargs(vector: list[float], filter_expression: Any | None = None) -> dict[str, Any]
```

Convert config to VectorQuery kwargs, excluding None version-dependent params.

Parameters:

| Name                | Type          | Description                 | Default                              |
| ------------------- | ------------- | --------------------------- | ------------------------------------ |
| `vector`            | `list[float]` | The query vector embedding. | *required*                           |
| `filter_expression` | \`Any         | None\`                      | Optional filter expression to apply. |

Returns:

| Type             | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| `dict[str, Any]` | Dictionary of kwargs suitable for VectorQuery constructor. |

Source code in `src/adk_redis/tools/search/_config.py`

```python
def to_query_kwargs(
    self, vector: list[float], filter_expression: Any | None = None
) -> dict[str, Any]:
  """Convert config to VectorQuery kwargs, excluding None version-dependent params.

  Args:
      vector: The query vector embedding.
      filter_expression: Optional filter expression to apply.

  Returns:
      Dictionary of kwargs suitable for VectorQuery constructor.
  """
  # Core parameters always included
  kwargs: dict[str, Any] = {
      "vector": vector,
      "vector_field_name": self.vector_field_name,
      "num_results": self.num_results,
      "dtype": self.dtype,
      "return_score": self.return_score,
      "dialect": self.dialect,
      "sort_by": self.sort_by,
      "in_order": self.in_order,
      "normalize_vector_distance": self.normalize_vector_distance,
      "filter_expression": filter_expression,
  }

  # Version-dependent parameters: only include if not None
  version_dependent = {
      "hybrid_policy": self.hybrid_policy,
      "batch_size": self.batch_size,
      "ef_runtime": self.ef_runtime,
      "search_window_size": self.search_window_size,
      "use_search_history": self.use_search_history,
      "search_buffer_capacity": self.search_buffer_capacity,
  }
  for key, value in version_dependent.items():
    if value is not None:
      kwargs[key] = value

  return kwargs
```

### RedisVectorSearchTool

```python
RedisVectorSearchTool(*, index: SearchIndex | AsyncSearchIndex, vectorizer: BaseVectorizer, config: RedisVectorQueryConfig | None = None, return_fields: list[str] | None = None, filter_expression: Any | None = None, name: str = 'redis_vector_search', description: str = 'Search for semantically similar documents using vector similarity with Redis.')
```

Bases: `VectorizedSearchTool`

Vector similarity search tool using RedisVL.

This tool performs K-nearest neighbor (KNN) vector similarity search over a Redis index. It embeds the query text using the provided vectorizer and finds the most similar documents.

Example

```python
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer
from redisvl.query.filter import Tag
from adk_redis import (
    RedisVectorSearchTool,
    RedisVectorQueryConfig,
)

index = SearchIndex.from_yaml("schema.yaml")
vectorizer = HFTextVectorizer(model="redis/langcache-embed-v2")

# Using config object (recommended)
config = RedisVectorQueryConfig(
    num_results=5,
    ef_runtime=100,  # Higher = better recall
)
tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=config,
    return_fields=["title", "content", "url"],
    filter_expression=Tag("category") == "redis",
)

# Use with an agent
agent = Agent(model="gemini-2.5-flash", tools=[tool])
```

Initialize the vector search tool.

Parameters:

| Name                | Type                     | Description                                   | Default                                                                                                                                                                                                                           |
| ------------------- | ------------------------ | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `index`             | \`SearchIndex            | AsyncSearchIndex\`                            | The RedisVL SearchIndex to query.                                                                                                                                                                                                 |
| `vectorizer`        | `BaseVectorizer`         | The vectorizer for embedding queries.         | *required*                                                                                                                                                                                                                        |
| `config`            | \`RedisVectorQueryConfig | None\`                                        | Configuration for query parameters. If None, uses defaults. See RedisVectorQueryConfig for available options including num_results, vector_field_name, dtype, and version-dependent parameters like ef_runtime and hybrid_policy. |
| `return_fields`     | \`list[str]              | None\`                                        | Optional list of fields to return in results.                                                                                                                                                                                     |
| `filter_expression` | \`Any                    | None\`                                        | Optional RedisVL FilterExpression to narrow results.                                                                                                                                                                              |
| `name`              | `str`                    | The name of the tool (exposed to LLM).        | `'redis_vector_search'`                                                                                                                                                                                                           |
| `description`       | `str`                    | The description of the tool (exposed to LLM). | `'Search for semantically similar documents using vector similarity with Redis.'`                                                                                                                                                 |

Source code in `src/adk_redis/tools/search/vector.py`

```python
def __init__(
    self,
    *,
    index: SearchIndex | AsyncSearchIndex,
    vectorizer: BaseVectorizer,
    config: RedisVectorQueryConfig | None = None,
    return_fields: list[str] | None = None,
    filter_expression: Any | None = None,
    name: str = "redis_vector_search",
    description: str = "Search for semantically similar documents using vector similarity with Redis.",
):
  """Initialize the vector search tool.

  Args:
      index: The RedisVL SearchIndex to query.
      vectorizer: The vectorizer for embedding queries.
      config: Configuration for query parameters. If None, uses defaults.
          See RedisVectorQueryConfig for available options including
          num_results, vector_field_name, dtype, and version-dependent
          parameters like ef_runtime and hybrid_policy.
      return_fields: Optional list of fields to return in results.
      filter_expression: Optional RedisVL FilterExpression to narrow results.
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      vectorizer=vectorizer,
      return_fields=return_fields,
  )
  self._config = config or RedisVectorQueryConfig()
  self._filter_expression = filter_expression
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the vector-based search query.

Parameters:

| Name           | Type             | Description                                   | Default    |
| -------------- | ---------------- | --------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM, must include 'query'. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                   | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status, count, and results. |

Source code in `src/adk_redis/tools/search/_base.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the vector-based search query.

  Args:
      args: Arguments from the LLM, must include 'query'.
      tool_context: The tool execution context.

  Returns:
      A dictionary with status, count, and results.
  """

  async def build_query_fn(query_text: str, args: dict[str, Any]) -> Any:
    embedding = await self._vectorizer.aembed(query_text)
    return self._build_query(query_text, embedding, **args)

  return await self._run_search(args, build_query_fn)
```

### VectorizedSearchTool

```python
VectorizedSearchTool(*, name: str, description: str, index: SearchIndex | AsyncSearchIndex, vectorizer: BaseVectorizer, return_fields: list[str] | None = None)
```

Bases: `BaseRedisSearchTool`

Base class for Redis search tools that require vector embeddings.

This class extends BaseRedisSearchTool with:

- Required vectorizer for embedding queries
- Abstract \_build_query method for subclasses to implement

Use this as the base class for vector-based search tools like VectorSearchTool, HybridSearchTool, and RangeSearchTool.

Initialize the vectorized search tool.

Parameters:

| Name            | Type             | Description                                      | Default                                               |
| --------------- | ---------------- | ------------------------------------------------ | ----------------------------------------------------- |
| `name`          | `str`            | The name of the tool (exposed to LLM).           | *required*                                            |
| `description`   | `str`            | The description of the tool (exposed to LLM).    | *required*                                            |
| `index`         | \`SearchIndex    | AsyncSearchIndex\`                               | The RedisVL SearchIndex or AsyncSearchIndex to query. |
| `vectorizer`    | `BaseVectorizer` | The vectorizer for embedding queries (required). | *required*                                            |
| `return_fields` | \`list[str]      | None\`                                           | Optional list of fields to return in results.         |

Source code in `src/adk_redis/tools/search/_base.py`

```python
def __init__(
    self,
    *,
    name: str,
    description: str,
    index: SearchIndex | AsyncSearchIndex,
    vectorizer: BaseVectorizer,
    return_fields: list[str] | None = None,
):
  """Initialize the vectorized search tool.

  Args:
      name: The name of the tool (exposed to LLM).
      description: The description of the tool (exposed to LLM).
      index: The RedisVL SearchIndex or AsyncSearchIndex to query.
      vectorizer: The vectorizer for embedding queries (required).
      return_fields: Optional list of fields to return in results.
  """
  super().__init__(
      name=name,
      description=description,
      index=index,
      return_fields=return_fields,
  )
  self._vectorizer = vectorizer
```

#### run_async

```python
run_async(*, args: dict[str, Any], tool_context: ToolContext) -> dict[str, Any]
```

Execute the vector-based search query.

Parameters:

| Name           | Type             | Description                                   | Default    |
| -------------- | ---------------- | --------------------------------------------- | ---------- |
| `args`         | `dict[str, Any]` | Arguments from the LLM, must include 'query'. | *required* |
| `tool_context` | `ToolContext`    | The tool execution context.                   | *required* |

Returns:

| Type             | Description                                   |
| ---------------- | --------------------------------------------- |
| `dict[str, Any]` | A dictionary with status, count, and results. |

Source code in `src/adk_redis/tools/search/_base.py`

```python
async def run_async(
    self, *, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
  """Execute the vector-based search query.

  Args:
      args: Arguments from the LLM, must include 'query'.
      tool_context: The tool execution context.

  Returns:
      A dictionary with status, count, and results.
  """

  async def build_query_fn(query_text: str, args: dict[str, Any]) -> Any:
    embedding = await self._vectorizer.aembed(query_text)
    return self._build_query(query_text, embedding, **args)

  return await self._run_search(args, build_query_fn)
```

### create_memory_mcp_toolset

```python
create_memory_mcp_toolset(server_url: str = 'http://localhost:8000', tool_filter: list[str] | None = None) -> 'McpToolset'
```

Create an MCP toolset for Agent Memory Server.

This function creates an McpToolset configured to connect to the Agent Memory Server's SSE endpoint. The toolset provides access to all memory operations via the Model Context Protocol.

Parameters:

| Name          | Type        | Description                                                                                 | Default                                                                                                                                                                                                                                                                 |
| ------------- | ----------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `server_url`  | `str`       | Base URL of the Agent Memory Server (without /sse suffix). Default: "http://localhost:8000" | `'http://localhost:8000'`                                                                                                                                                                                                                                               |
| `tool_filter` | \`list[str] | None\`                                                                                      | Optional list of tool names to expose. If None, all available tools are exposed. Available tools: - search_long_term_memory - get_long_term_memory - create_long_term_memories - edit_long_term_memory - delete_long_term_memories - memory_prompt - set_working_memory |

Returns:

| Type           | Description                                    |
| -------------- | ---------------------------------------------- |
| `'McpToolset'` | McpToolset configured for Agent Memory Server. |

Raises:

| Type          | Description                                      |
| ------------- | ------------------------------------------------ |
| `ImportError` | If google-adk is not installed with MCP support. |

Example

```python
from google.adk import Agent
from adk_redis.tools.mcp_memory import create_memory_mcp_toolset

# All memory tools
all_tools = create_memory_mcp_toolset(
    server_url="http://localhost:8000",
)

# Only search and create tools
limited_tools = create_memory_mcp_toolset(
    server_url="http://localhost:8000",
    tool_filter=["search_long_term_memory", "create_long_term_memories"],
)

agent = Agent(
    model="gemini-2.0-flash",
    name="memory_agent",
    tools=[limited_tools],
)
```

Source code in `src/adk_redis/tools/mcp_memory.py`

````python
def create_memory_mcp_toolset(
    server_url: str = "http://localhost:8000",
    tool_filter: list[str] | None = None,
) -> "McpToolset":
  """Create an MCP toolset for Agent Memory Server.

  This function creates an McpToolset configured to connect to the
  Agent Memory Server's SSE endpoint. The toolset provides access to
  all memory operations via the Model Context Protocol.

  Args:
      server_url: Base URL of the Agent Memory Server (without /sse suffix).
          Default: "http://localhost:8000"
      tool_filter: Optional list of tool names to expose. If None, all
          available tools are exposed. Available tools:
          - search_long_term_memory
          - get_long_term_memory
          - create_long_term_memories
          - edit_long_term_memory
          - delete_long_term_memories
          - memory_prompt
          - set_working_memory

  Returns:
      McpToolset configured for Agent Memory Server.

  Raises:
      ImportError: If google-adk is not installed with MCP support.

  Example:
      ```python
      from google.adk import Agent
      from adk_redis.tools.mcp_memory import create_memory_mcp_toolset

      # All memory tools
      all_tools = create_memory_mcp_toolset(
          server_url="http://localhost:8000",
      )

      # Only search and create tools
      limited_tools = create_memory_mcp_toolset(
          server_url="http://localhost:8000",
          tool_filter=["search_long_term_memory", "create_long_term_memories"],
      )

      agent = Agent(
          model="gemini-2.0-flash",
          name="memory_agent",
          tools=[limited_tools],
      )
      ```
  """
  try:
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import (
        SseConnectionParams,
    )
  except ImportError as e:
    raise ImportError(
        "google-adk with MCP support is required. "
        "Install it with: pip install google-adk[mcp]"
    ) from e

  # Ensure URL doesn't have trailing slash and add /sse endpoint
  base_url = server_url.rstrip("/")
  sse_url = f"{base_url}/sse"

  return McpToolset(
      connection_params=SseConnectionParams(url=sse_url),
      tool_filter=tool_filter,
  )
````
