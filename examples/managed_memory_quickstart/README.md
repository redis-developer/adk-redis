# Managed Redis Agent Memory Quickstart

Minimal counterpart to [`simple_redis_memory`](../simple_redis_memory/). This
example uses the **managed** `redis-agent-memory` backend (the library default)
with no self-hosted Agent Memory Server or Docker setup.

## What it demonstrates

- `RedisSessionMemoryService` for session persistence
- `RedisLongTermMemoryService` for semantic memory search
- ADK built-in `preload_memory` and `load_memory` tools

This example intentionally avoids opensource-only features such as
auto-summarization, extraction strategies, recency-boosted search, and MCP.

## Prerequisites

- Python 3.10+
- A Redis Agent Memory store (`REDIS_AGENT_MEMORY_STORE_ID` + API key)
- Google API key for Gemini

## Setup

### 1. Install dependencies

From the repository root (editable install for local PR testing):

```bash
uv venv
uv pip install -e ".[all,examples]"
```

Or use `make dev` if you also want test/lint tooling.

> **Note:** Even memory-only examples import `adk_redis`, whose top-level
> `__init__.py` currently pulls in search tools that require `redisvl`. The
> `[all]` extra installs that dependency. `[memory]` alone is not enough today.

### 2. Configure environment

```bash
cd examples/managed_memory_quickstart
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start the agent

```bash
uv run python main.py
```

Open http://localhost:8080 in your browser.

## Try it

**Session 1** — share a few facts:

```
Hi! My name is Alex.
My favorite color is teal.
I have a cat named Sammy.
```

Wait for a reply after each message.

**Session 2** — click **New Session** (keep the same `userId`, e.g. `user`) and
ask:

```
What do you remember about me?
What is my favorite color?
```

Cross-session recall uses long-term memory (`preload_memory` / `load_memory`).
Facts are stored automatically after each turn via the agent's `after_agent`
callback — there is no separate seed step.

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | — | Gemini API key |
| `REDIS_AGENT_MEMORY_API_BASE_URL` | Yes | — | Managed API base URL |
| `REDIS_AGENT_MEMORY_API_KEY` | Yes | — | Managed API key |
| `REDIS_AGENT_MEMORY_STORE_ID` | Yes | — | Memory store ID |
| `REDIS_MEMORY_NAMESPACE` | No | `managed_memory_quickstart` | Namespace for isolation |
| `REDIS_MEMORY_SEARCH_TOP_K` | No | `5` | Results returned by `search_memory` |
| `PORT` | No | `8080` | ADK web server port |

## How to run

This example uses a custom `main.py` with `get_fast_api_app` because ADK
session and memory services must be registered through
`get_service_registry()`. The `adk web` runner cannot register those services.

For a tools-only example that runs with `adk web`, see
[`travel_agent_memory_tools`](../travel_agent_memory_tools/).

## Related examples

| Example | Backend | Runner |
|---------|---------|--------|
| **This quickstart** | Managed (`redis-agent-memory`) | `python main.py` |
| [`simple_redis_memory`](../simple_redis_memory/) | Self-hosted (default) | `python main.py` |
| [`travel_agent_memory_tools`](../travel_agent_memory_tools/) | Either (env switch) | `adk web .` |

See [`examples/README.md`](../README.md) for the full matrix.
