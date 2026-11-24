# Redis Iris with Google ADK

Run one clinic support turn with five Iris services. Intent Router selects an
ADK agent. Agent Playbooks supplies published guidance, Agent Memory persists
the session and recalls preferences for the current user, and Context Gateway
exposes the live clinic directory as tools. Lens records the turn.

## Set up the services

Use Python 3.11 or later, [uv](https://docs.astral.sh/uv/), a Gemini API key, and
Iris services with runtime agent keys. Copy `.env.example` to `.env` in this
directory and fill in the connection values. The commands below run from the
repository root.

1. [Agent Memory](https://redis.io/docs/latest/develop/ai/context-engine/agent-memory/quickstart/).
   Use a store with namespace support. The default namespace name is
   `adk-iris-support`. The adapter creates the shared root if needed, so a
   key that cannot create namespaces needs a precreated namespace ID in
   `IRIS_DEMO_NAMESPACE`. Use demo data with the sample user `demo-customer`.
2. [Agent Playbooks](https://redis.io/docs/latest/develop/ai/context-engine/agent-playbooks/quickstart/).
   Publish an FAQ for “How do I book an appointment?” and a clinic directory
   skill that tells the agent to query the provider filter in Context Gateway,
   count results by clinic, and identify the clinic with the most matches.
   Use “Which clinic has the most cardiologists?” in the skill description to
   help it match the demo question. The SDK loads the best matching published
   skill when its score meets the hook threshold.
3. [Context Gateway](https://redis.io/docs/latest/develop/ai/context-engine/context-gateway/quickstart/).
   Load the sample clinic directory and use the full-mode Gateway's MCP
   endpoint. `IrisGatewayToolset` discovers `scheduling__filter_provider`
   and exposes its schema directly to ADK.
4. [Intent Router](https://redis.io/docs/latest/develop/ai/context-engine/intent-router/quickstart/).
   Define an intent named `clinic_search` with target
   `{"type":"agent","ref":"clinic_search"}` and example phrases such as
   “Which clinic has the most cardiologists, and how many does it have?” and
   “Find a clinic with cardiologists.” Use a runtime key with read access.
5. [Lens](https://redis.io/docs/latest/develop/ai/context-engine/lens/quickstart/).
   Set the ingest endpoint and the key used to send traces. The command
   below installs the tracing extra for model instrumentation.

## Run and inspect a turn

```bash
uv run --locked --extra iris --extra examples python examples/iris_suite/main.py \
  "Which clinic has the most cardiologists, and how many does it have?"
```

Expect the `clinic_search` agent and, with the unchanged sample records,
`clinic-a` with two cardiologists. Look up the printed trace ID in Lens to
inspect the turn. Use the session ID to check the corresponding conversation
in Agent Memory. Use `--session-id` with the printed session ID to
continue the conversation. A message with no matching intent goes to
`general_support`.

To see a long-term recall, add a demo preference in Agent Memory with owner
`demo-customer` and the same namespace ID. For example, save “The customer
prefers appointments in the morning,” then ask the agent to include that
preference when summarizing the clinic results. For the write call, see
[Place and retrieve memories](https://redis.io/docs/latest/develop/ai/context-engine/agent-memory/namespaces/#place-and-retrieve-memories).
The adapter's recall filters on both the configured namespace and the user ID.

## Optional Agent Mesh beta

This local example uses an in-memory ADK session, Gemini, and a separate Redis
database for resumable SSE. Only the Gemini and Redis settings from `.env`
are needed. The `mesh` extra installs both Mesh transports and requires
Redis 8 client libraries. Keep this demo on loopback. A shared deployment must authorize
both the start and read endpoints.

Run Redis 8.6.2 or later with native producer idempotency. For example:

```bash
docker run --rm -p 127.0.0.1:6386:6379 redis:8.6.6-alpine
```

In a separate terminal, run:

```bash
uv run --locked --extra mesh --extra examples python examples/iris_suite/mesh.py
```

Start a turn. Copy the returned `stream_id` into `RUN_ID`:

```bash
curl -sS -X POST http://127.0.0.1:8080/runs \
  -H 'Content-Type: application/json' \
  -d '{"text":"Explain how a Redis stream keeps entries in order."}'
```

Subscribe, then interrupt the connection after receiving a `delta`. Copy its
`id:` value into `CURSOR` and reconnect. The second request receives events
after that cursor, including the terminal `message` if it was retained.

```bash
curl -N "http://127.0.0.1:8080/runs/$RUN_ID/events"
curl -N -H "Last-Event-ID: $CURSOR" \
  "http://127.0.0.1:8080/runs/$RUN_ID/events"
```

Replay also works after the producer finishes and before the retention window
expires. See the
[Agent Mesh FastAPI guide](https://redis.io/docs/latest/develop/ai/context-engine/agent-mesh/fastapi-sse-sdk/)
for SDK beta limits.

## Use the integrations in your own app

Install `adk-redis[iris]` with Python 3.11 or later. The adapters read the
same `IRIS_*` environment variables as the Redis Iris SDK and also accept
configured clients. Enable only the adapters your application uses.

| Capability | Public API |
| --- | --- |
| Agent Memory | Pass `RedisSessionMemoryService` and `RedisLongTermMemoryService` to an ADK `Runner`. |
| Agent Playbooks | Add `IrisPlaybooksPlugin()` to `App.plugins` for published FAQs and skill instructions on model requests. Pass SDK hooks to configure the retrieval policy. |
| Context Gateway | Add `IrisGatewayToolset()` to an agent's tools. Full mode exposes catalog tools and search mode exposes the Gateway's search, dispatch, and result tools. Use `tool_filter` to control the exposed tool names. |
| Intent Router | Call `await IrisIntentRouter(routes, fallback=runner).select(message)`. Key `routes` by `(target.type, target.ref)` and register the agents, runners, or handlers your app permits. |
| Lens | Initialize `IrisLens(agent_id=...)` at startup. Use `run_async()` to trace the runner or `turn()` to include routing and retrieval before the runner. Use one turn boundary per invocation and call `shutdown()` at process exit. |
| Agent Mesh SSE | Install `adk-redis[mesh]`. Pass `stream_adk_turn()` to the Mesh backend's producer. The app owns the session, stream scope, and authorization. |

When consuming `IrisLens.run_async()`, use `contextlib.aclosing` if the
consumer might break out of async iteration before the runner finishes.

### Agent Mesh A2A

The `mesh` extra also provides an A2A app factory for an existing ADK runner:

```python
from adk_redis.iris.a2a import create_mesh_a2a_app

app = create_mesh_a2a_app(
    runner=runner,
    agent_card=agent_card,
    commands=redis_commands,
    readers=redis_readers,
    namespace="support:a2a",
    auth_backend=auth_backend,
)
```

Supply an A2A agent card, separate asynchronous Redis clients for commands
and blocking readers, and a Starlette authentication backend that supplies a
stable, unique principal as the user display name. The server authorizes each
subscription and uses the same identity to scope ADK sessions. Your app owns
the runner and Redis clients. In a multi-replica deployment, share the ADK
session backend, Redis database, and namespace. The A2A app exposes resumable
HTTP+JSON streams. Send `A2A-Version: 1.0` and the last received
`Last-Event-ID` when reconnecting. See the
[Agent Mesh A2A guide](https://redis.io/docs/latest/develop/ai/context-engine/agent-mesh/a2a-sdk/)
for task version, retention, and reconnect behavior.
