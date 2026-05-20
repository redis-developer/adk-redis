# Session Service

This guide shows how to wire `RedisSessionService` into a Google ADK agent for durable session state.

## Prerequisites

- Redis running on `localhost:6379`
- `adk-redis` installed: `pip install adk-redis`

## Basic usage

```python
from google.adk.agents import Agent
from adk_redis import RedisSessionService

# Create Redis-backed session service
session_service = RedisSessionService(
    redis_url="redis://localhost:6379",
    app_name="my-agent",
)

# Create your ADK agent with Redis sessions
agent = Agent(
    model="gemini-2.0-flash",
    name="my_agent",
    instruction="You are a helpful assistant.",
)

# Create a session
session = await session_service.create_session(
    app_name="my-agent",
    user_id="alice",
)

# The session is now persisted in Redis and survives process restarts
```

## Configuration options

| Option       | Default                  | Description             |
| ------------ | ------------------------ | ----------------------- |
| `redis_url`  | `redis://localhost:6379` | Redis connection string |
| `app_name`   | Required                 | Application namespace   |
| `ttl`        | `None`                   | Session TTL in seconds  |
| `key_prefix` | `adk:session`            | Redis key prefix        |
