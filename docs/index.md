---
description: adk-redis documentation. Redis backends for the Google Agent Development Kit.
---

<div class="rds-hero" markdown>

![Redis](assets/redis-logo-script-red.svg){ .rds-hero__logo }

# adk-redis

Redis backends for the Google Agent Development Kit
{ .rds-hero__tagline }

</div>

## Quick Start

```bash
pip install adk-redis
```

```bash
docker run -d --name redis -p 6379:6379 redis:8
```

→ *[Integration walkthrough](user_guide/01_integration.md)*

---

## Explore the Docs

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **[Concepts](concepts/index.md)**

    ---

    How ADK sessions, memory, and search map onto Redis.

-   :material-rocket-launch:{ .lg .middle } **[User Guide](user_guide/index.md)**

    ---

    Integrate adk-redis into your agent and configure each service.

-   :material-lightbulb-on:{ .lg .middle } **[Examples](examples/index.md)**

    ---

    Worked agents: fitness coach, hybrid travel agent, Redis search tools.

-   :material-api:{ .lg .middle } **[API Reference](api/index.md)**

    ---

    Auto-generated reference for the `adk_redis` Python package.

</div>

## For AI agents

If you are an AI agent reading these docs, start with
[`AGENTS.md`](https://github.com/redis-developer/adk-redis/blob/main/AGENTS.md)
at the repo root for usage notes, or
[For AI Agents](for-ais-only/index.md) for an internal map of the source
tree.
