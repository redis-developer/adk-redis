# Sessions

`RedisSessionService` stores ADK session state in Redis, making it durable and shareable across processes.

## How sessions are stored

Each session is a Redis JSON document keyed by `adk:session:{app_name}:{user_id}:{session_id}`. The document contains:

- **Messages** - The conversation history (user, agent, tool calls)
- **State** - Arbitrary key-value data for the session
- **Metadata** - Timestamps, app name, user ID

## TTL behavior

Sessions support configurable TTL:

- TTL is refreshed on every read or write
- Expired sessions are automatically cleaned up by Redis
- Default: no expiration (persistent until explicitly deleted)

## Cross-process semantics

Because sessions are stored in Redis (not in memory), multiple processes can share the same session. This enables:

- Horizontal scaling of ADK agents
- Seamless failover between instances
- Background workers that access session state
