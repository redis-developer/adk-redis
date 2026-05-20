# ADK Overview

The [Google Agent Development Kit (ADK)](https://github.com/google/adk-python) is a framework for building AI agents with Google's Gemini models. `adk-redis` provides Redis-backed implementations of ADK's service interfaces so you can move from prototype to production without rewriting your agent.

## Architecture

```mermaid
flowchart TD
    subgraph Agent [Your ADK Agent]
        SS[Session Service<br/>working memory]
        MS[Memory Service<br/>long-term]
        ST[Search Tools<br/>vector · hybrid · SQL]
        SC[Semantic Cache<br/>before/after callbacks]
    end

    SS & MS -->|REST / MCP| AMS
    ST -->|RedisVL / MCP| R
    SC -->|RedisVL / LangCache| R

    subgraph AMS [Agent Memory Server]
        WM[Working Memory API]
        LTM[Long-Term Memory API]
    end

    AMS --> R

    subgraph R [Redis 8.4+]
        JSON[(JSON storage)]
        VEC[(Vector index)]
        FTS[(Full-text index)]
    end
```

## ADK Interfaces

`adk-redis` implements four ADK extension points. Each one maps to a concept page with full details.

| ADK Interface | `adk-redis` implementation | Concept page |
|---------------|---------------------------|-------------|
| `BaseSessionService` | `RedisWorkingMemorySessionService` | [Sessions + Memory Services](sessions.md) |
| `BaseMemoryService` | `RedisLongTermMemoryService` | [Sessions + Memory Services](sessions.md) |
| `BaseTool` | Search tools (`RedisVectorSearchTool`, `RedisHybridSearchTool`, etc.) and memory tools (`SearchMemoryTool`, `CreateMemoryTool`, etc.) | [Search Tools](search.md), [Memory MCP + Tools](memory.md) |
| Model callbacks | `LLMResponseCache` with `RedisVLCacheProvider` or `LangCacheProvider` | [Semantic Caching](caching.md) |

## Running Your Agent

ADK provides several ways to run and test agents:

- **`adk web`**: browser-based UI for interactive development and debugging.
- **`adk run`**: terminal-based interaction.
- **`adk api_server`**: RESTful API for production deployment.

See the [ADK runtime documentation](https://google.github.io/adk-docs/runtime/) for details.
