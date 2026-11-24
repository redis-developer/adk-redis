---
description: Python API reference for Redis Iris integrations in Google ADK.
---

# Redis Iris

Use Python 3.11 or later for these integrations:

```bash
pip install 'adk-redis[iris]'
```

The `iris` extra includes [Agent Memory](memory.md) and its
[session service](sessions.md). The adapters use the Redis Iris SDK
connection settings. Use the runnable [Iris suite example](../../examples/index.md)
for service setup and a turn that exercises all five runtime services.

## Agent Playbooks

Register the plugin on `google.adk.apps.app.App.plugins`. On each model
request, it uses the original user message to retrieve published guidance
and appends that guidance to the model instructions.

::: adk_redis.iris.IrisPlaybooksPlugin
    options:
      inherited_members: false

## Context Gateway

Add the toolset to an ADK agent's `tools`. Full mode exposes the Gateway
catalog. Search mode exposes the Gateway's discovery, dispatch, and result
tools. The toolset passes the selected tool's published JSON schema to ADK.

::: adk_redis.iris.IrisGatewayToolset
    options:
      inherited_members: false

## Intent Router

Select a registered ADK agent, runner, or workflow before invoking it.
Register targets by the `(type, ref)` tuple configured in Iris. The fallback
handles empty queries, no matches, and targets outside the app's registry.

::: adk_redis.iris.IrisIntentRouter
    options:
      inherited_members: false

## Lens

Use `run_async()` to trace an ADK invocation. Use `turn()` when the trace
should also include routing or other work before the invocation. Pick one
turn boundary per invocation. The application calls `shutdown()` at
process exit to flush Lens.

::: adk_redis.iris.IrisLens
    options:
      inherited_members: false

## Agent Mesh beta

Install the transport extra for FastAPI SSE and A2A. Both require Redis 8.6.2
or later with `XADD IDMP`. A2A also requires Redis JSON support.

```bash
pip install 'adk-redis[mesh]'
```

### FastAPI SSE

Run the producer through the Mesh backend. The application creates the ADK
session and authorizes the stream scope on the start and read endpoints.

::: adk_redis.iris.stream_adk_turn

### A2A

Use the app factory with an ADK runner, an agent card, separate Redis
clients for commands and subscriptions, and an authentication backend.
Use a shared ADK session service if replicas can receive follow-up messages.

::: adk_redis.iris.a2a.create_mesh_a2a_app
