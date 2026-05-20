---
description: Foundational concepts for adk-redis.
---

# Concepts

`adk-redis` maps Google ADK service interfaces onto Redis, the Agent Memory
Server, and RedisVL. These pages explain the **what** and **why** behind each
feature. For step-by-step setup instructions, see the
[User Guide](../user_guide/index.md).

There are four ways to use this integration. Pick the page that matches your goal.

<div class="grid cards" markdown>

-   :material-google:{ .lg .middle } **[ADK overview](adk_overview.md)**

    ---

    Architecture diagram and the ADK interfaces this package implements.

-   :material-brain:{ .lg .middle } **[Sessions + Memory Services](sessions.md)**

    ---

    Framework-managed sessions and memory. The ADK Runner handles everything automatically.

-   :material-tools:{ .lg .middle } **[Sessions + Memory MCP + Tools](memory.md)**

    ---

    LLM-controlled memory via MCP or REST-based tools. The agent decides when to remember and recall.

-   :material-database-search:{ .lg .middle } **[RedisVL MCP + Search Tools](search.md)**

    ---

    Vector, hybrid, range, text, and SQL search over your own data via in-process tools or MCP.

-   :material-cached:{ .lg .middle } **[Semantic Caching](caching.md)**

    ---

    Skip repeat LLM calls with self-hosted (RedisVL) or managed (LangCache) semantic caching.

</div>

## Where to Start

| Goal | Read this |
|------|-----------|
| Understand the big picture | [ADK overview](adk_overview.md) |
| Let the framework manage sessions and memory | [Sessions + Memory Services](sessions.md) |
| Give the LLM explicit memory tools | [Sessions + Memory MCP + Tools](memory.md) |
| Search your own knowledge base | [RedisVL MCP + Search Tools](search.md) |
| Reduce LLM latency and cost | [Semantic Caching](caching.md) |
| Get a working agent running | [Quickstart](../user_guide/01_integration.md) |
| Run and test your agent | [ADK runtime](https://google.github.io/adk-docs/runtime/) |
