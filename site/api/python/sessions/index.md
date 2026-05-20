# sessions

## sessions

Redis session services for ADK.

### RedisWorkingMemorySessionService

```python
RedisWorkingMemorySessionService(config: RedisWorkingMemorySessionServiceConfig | None = None)
```

Bases: `BaseSessionService`

Session service using Redis Agent Memory Server's Working Memory API.

This service provides session management backed by Agent Memory Server:

- Session storage in Working Memory
- Automatic context summarization when token limit exceeded
- Background memory extraction to Long-Term Memory
- Incremental message appending
- https://github.com/redis/agent-memory-server

Requires the `agent-memory-client` package to be installed.

Example

```python
from adk_redis import (
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

config = RedisWorkingMemorySessionServiceConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
)
session_service = RedisWorkingMemorySessionService(config=config)

# Use with ADK runner
runner = Runner(
    agent=agent,
    session_service=session_service,
)
```

Initialize the Redis Working Memory Session Service.

Parameters:

| Name     | Type                                     | Description | Default                                                |
| -------- | ---------------------------------------- | ----------- | ------------------------------------------------------ |
| `config` | \`RedisWorkingMemorySessionServiceConfig | None\`      | Configuration for the service. If None, uses defaults. |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
def __init__(
    self, config: RedisWorkingMemorySessionServiceConfig | None = None
):
  """Initialize the Redis Working Memory Session Service.

  Args:
      config: Configuration for the service. If None, uses defaults.
  """
  self._config = config or RedisWorkingMemorySessionServiceConfig()
```

#### create_session

```python
create_session(*, app_name: str, user_id: str, state: dict[str, Any] | None = None, session_id: str | None = None) -> Session
```

Create a new session in Working Memory.

Uses get_or_create_working_memory to prevent accidental overwrites of existing sessions.

Parameters:

| Name         | Type             | Description                                             | Default                                          |
| ------------ | ---------------- | ------------------------------------------------------- | ------------------------------------------------ |
| `app_name`   | `str`            | Application name (used as namespace if not configured). | *required*                                       |
| `user_id`    | `str`            | User identifier.                                        | *required*                                       |
| `state`      | \`dict[str, Any] | None\`                                                  | Initial session state.                           |
| `session_id` | \`str            | None\`                                                  | Optional session ID (generated if not provided). |

Returns:

| Type      | Description          |
| --------- | -------------------- |
| `Session` | The created Session. |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
@override
async def create_session(
    self,
    *,
    app_name: str,
    user_id: str,
    state: dict[str, Any] | None = None,
    session_id: str | None = None,
) -> Session:
  """Create a new session in Working Memory.

  Uses get_or_create_working_memory to prevent accidental overwrites
  of existing sessions.

  Args:
      app_name: Application name (used as namespace if not configured).
      user_id: User identifier.
      state: Initial session state.
      session_id: Optional session ID (generated if not provided).

  Returns:
      The created Session.
  """
  from agent_memory_client.models import MemoryStrategyConfig

  session_id = (
      session_id.strip()
      if session_id and session_id.strip()
      else str(uuid.uuid4())
  )
  namespace = self._get_namespace(app_name)

  strategy_config = MemoryStrategyConfig(
      strategy=self._config.extraction_strategy,
      config=self._config.extraction_strategy_config,
  )

  # Use get_or_create to prevent accidental overwrites
  client = self._get_client()
  created, working_memory = await client.get_or_create_working_memory(
      session_id=session_id,
      namespace=namespace,
      user_id=user_id,
      long_term_memory_strategy=strategy_config,
  )

  if not created:
    logger.warning(
        "Session %s already exists in namespace %s, returning existing",
        session_id,
        namespace,
    )
    # Return existing session data
    return self._working_memory_response_to_session(
        working_memory, app_name, user_id
    )

  # Update with initial state and TTL if provided
  if state or self._config.session_ttl_seconds:
    if state:
      working_memory.data = state
    if self._config.session_ttl_seconds:
      working_memory.ttl_seconds = self._config.session_ttl_seconds
    await client.put_working_memory(
        session_id=session_id,
        memory=working_memory,
        user_id=user_id,
    )

  logger.info("Created session %s in namespace %s", session_id, namespace)

  return Session(
      id=session_id,
      app_name=app_name,
      user_id=user_id,
      state=state or {},
      events=[],
      last_update_time=time.time(),
  )
```

#### get_session

```python
get_session(*, app_name: str, user_id: str, session_id: str, config: GetSessionConfig | None = None) -> Session | None
```

Retrieve a session from Working Memory.

Uses get_or_create_working_memory and checks if session was newly created to determine if it exists. Passes model_name and context_window_max to enable automatic context summarization when token limit is exceeded.

NOTE: For ADK Runner compatibility, this method now returns the session even if it was just created. The Runner expects get_session to either return an existing session OR return a newly created empty session. Returning None causes the Runner to fail with "Session not found".

Parameters:

| Name         | Type               | Description             | Default                                      |
| ------------ | ------------------ | ----------------------- | -------------------------------------------- |
| `app_name`   | `str`              | Application name.       | *required*                                   |
| `user_id`    | `str`              | User identifier.        | *required*                                   |
| `session_id` | `str`              | Session ID to retrieve. | *required*                                   |
| `config`     | \`GetSessionConfig | None\`                  | Optional configuration for filtering events. |

Returns:

| Type      | Description |
| --------- | ----------- |
| \`Session | None\`      |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
@override
async def get_session(
    self,
    *,
    app_name: str,
    user_id: str,
    session_id: str,
    config: GetSessionConfig | None = None,
) -> Session | None:
  """Retrieve a session from Working Memory.

  Uses get_or_create_working_memory and checks if session was newly created
  to determine if it exists. Passes model_name and context_window_max to
  enable automatic context summarization when token limit is exceeded.

  NOTE: For ADK Runner compatibility, this method now returns the session
  even if it was just created. The Runner expects get_session to either
  return an existing session OR return a newly created empty session.
  Returning None causes the Runner to fail with "Session not found".

  Args:
      app_name: Application name.
      user_id: User identifier.
      session_id: Session ID to retrieve.
      config: Optional configuration for filtering events.

  Returns:
      The Session (existing or newly created).
  """
  from agent_memory_client.exceptions import MemoryNotFoundError

  try:
    namespace = self._get_namespace(app_name)
    # Use get_or_create to avoid deprecated get_working_memory
    client = self._get_client()
    created, response = await client.get_or_create_working_memory(
        session_id=session_id,
        namespace=namespace,
        user_id=user_id,
        model_name=self._config.model_name,
        context_window_max=self._config.context_window_max,
    )

    # Return the session whether it was just created or already existed
    # This is required for ADK Runner compatibility
    session = self._working_memory_response_to_session(
        response, app_name, user_id
    )

    if config:
      if config.num_recent_events:
        session.events = session.events[-config.num_recent_events :]
      if config.after_timestamp:
        session.events = [
            e for e in session.events if e.timestamp > config.after_timestamp
        ]

    return session

  except MemoryNotFoundError:
    return None
  except Exception as e:
    logger.error("Failed to get session %s: %s", session_id, e)
    return None
```

#### list_sessions

```python
list_sessions(*, app_name: str, user_id: str | None = None) -> ListSessionsResponse
```

List all sessions for a user from Working Memory.

Parameters:

| Name       | Type  | Description       | Default                                             |
| ---------- | ----- | ----------------- | --------------------------------------------------- |
| `app_name` | `str` | Application name. | *required*                                          |
| `user_id`  | \`str | None\`            | User identifier (required for this implementation). |

Returns:

| Type                   | Description                                                |
| ---------------------- | ---------------------------------------------------------- |
| `ListSessionsResponse` | ListSessionsResponse containing sessions (without events). |

Raises:

| Type         | Description                 |
| ------------ | --------------------------- |
| `ValueError` | If user_id is not provided. |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
@override
async def list_sessions(
    self, *, app_name: str, user_id: str | None = None
) -> ListSessionsResponse:
  """List all sessions for a user from Working Memory.

  Args:
      app_name: Application name.
      user_id: User identifier (required for this implementation).

  Returns:
      ListSessionsResponse containing sessions (without events).

  Raises:
      ValueError: If user_id is not provided.
  """
  if user_id is None:
    raise ValueError(
        "user_id is required for RedisWorkingMemorySessionService"
    )
  try:
    namespace = self._get_namespace(app_name)

    # SDK method: list_sessions returns SessionListResponse
    # with sessions: list[str] (session IDs only)
    client = self._get_client()
    response = await client.list_sessions(
        namespace=namespace,
        user_id=user_id,
    )

    sessions = []
    for session_id in response.sessions:
      session = Session(
          id=session_id,
          app_name=app_name,
          user_id=user_id,
          state={},
          events=[],
          last_update_time=time.time(),
      )
      sessions.append(session)

    return ListSessionsResponse(sessions=sessions)

  except Exception as e:
    logger.error("Failed to list sessions: %s", e)
    return ListSessionsResponse(sessions=[])
```

#### delete_session

```python
delete_session(*, app_name: str, user_id: str, session_id: str) -> None
```

Delete a session from Working Memory.

Parameters:

| Name         | Type  | Description           | Default    |
| ------------ | ----- | --------------------- | ---------- |
| `app_name`   | `str` | Application name.     | *required* |
| `user_id`    | `str` | User identifier.      | *required* |
| `session_id` | `str` | Session ID to delete. | *required* |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
@override
async def delete_session(
    self, *, app_name: str, user_id: str, session_id: str
) -> None:
  """Delete a session from Working Memory.

  Args:
      app_name: Application name.
      user_id: User identifier.
      session_id: Session ID to delete.
  """
  try:
    namespace = self._get_namespace(app_name)
    client = self._get_client()
    await client.delete_working_memory(
        session_id=session_id,
        namespace=namespace,
        user_id=user_id,
    )
    logger.info("Deleted session %s", session_id)
  except Exception as e:
    logger.error("Failed to delete session %s: %s", session_id, e)
```

#### append_event

```python
append_event(session: Session, event: Event) -> Event
```

Append an event to the session in Working Memory.

Uses the incremental append API to add a single message without resending the full conversation history.

Parameters:

| Name      | Type      | Description               | Default    |
| --------- | --------- | ------------------------- | ---------- |
| `session` | `Session` | The session to append to. | *required* |
| `event`   | `Event`   | The event to append.      | *required* |

Returns:

| Type    | Description         |
| ------- | ------------------- |
| `Event` | The appended event. |

Source code in `src/adk_redis/sessions/working_memory.py`

```python
@override
async def append_event(self, session: Session, event: Event) -> Event:
  """Append an event to the session in Working Memory.

  Uses the incremental append API to add a single message without
  resending the full conversation history.

  Args:
      session: The session to append to.
      event: The event to append.

  Returns:
      The appended event.
  """
  await super().append_event(session=session, event=event)
  session.last_update_time = event.timestamp

  try:
    message = self._event_to_message(event)
    if message:
      namespace = self._get_namespace(session.app_name)
      client = self._get_client()
      await client.append_messages_to_working_memory(
          session_id=session.id,
          messages=[message],
          namespace=namespace,
          user_id=session.user_id,
      )
      logger.debug("Appended message to session %s", session.id)
  except Exception as e:
    logger.error("Failed to append event to session %s: %s", session.id, e)

  return event
```

#### close

```python
close() -> None
```

Close the session service and cleanup resources.

Source code in `src/adk_redis/sessions/working_memory.py`

```python
async def close(self) -> None:
  """Close the session service and cleanup resources."""
  # No longer caching client, so nothing to close
  pass
```

### RedisWorkingMemorySessionServiceConfig

Bases: `BaseModel`

Configuration for Redis Working Memory Session Service.

Attributes:

| Name                         | Type                                                      | Description                                |
| ---------------------------- | --------------------------------------------------------- | ------------------------------------------ |
| `api_base_url`               | `str`                                                     | Base URL of the Agent Memory Server.       |
| `timeout`                    | `float`                                                   | HTTP request timeout in seconds.           |
| `default_namespace`          | \`str                                                     | None\`                                     |
| `model_name`                 | \`str                                                     | None\`                                     |
| `context_window_max`         | \`int                                                     | None\`                                     |
| `extraction_strategy`        | `Literal['discrete', 'summary', 'preferences', 'custom']` | Memory extraction strategy.                |
| `extraction_strategy_config` | `dict[str, Any]`                                          | Additional config for extraction strategy. |
| `session_ttl_seconds`        | \`int                                                     | None\`                                     |
