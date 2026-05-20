# ADK Overview

The [Google Agent Development Kit (ADK)](https://github.com/google/adk-python) is a framework for building AI agents with Google's Gemini models. `adk-redis` provides Redis-backed implementations of ADK's service interfaces.

## ADK abstractions

| Abstraction | What it does                                     | Redis implementation          |
| ----------- | ------------------------------------------------ | ----------------------------- |
| **Agent**   | The reasoning core: plans, calls tools, responds | No change (ADK provides this) |
| **Session** | Conversation state across turns                  | `RedisSessionService`         |
| **Memory**  | Persistent knowledge across sessions             | `RedisMemoryService`          |
| **Tool**    | Functions the agent can call                     | RedisVL search tools          |

## Where Redis fits

Redis replaces the default in-memory implementations with durable, scalable alternatives:

- **Sessions** are stored as Redis JSON documents with optional TTL
- **Memory** is proxied to the Redis Agent Memory Server for two-tier storage
- **Search tools** use RedisVL for vector similarity search
- **Caching** uses Redis for semantic LLM response caching

## When to use adk-redis

Use `adk-redis` when you are building a Google ADK agent and need:

- Session persistence across process restarts
- Long-term memory that survives beyond a single conversation
- Vector search over your own documents
- Production deployment with Redis as the data layer
