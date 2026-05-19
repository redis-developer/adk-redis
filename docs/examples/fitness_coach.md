# Fitness Coach

A fitness coaching agent that uses MCP for memory operations and Redis for session persistence.

## What it demonstrates

- `RedisSessionService` for durable sessions
- MCP integration for accessing Agent Memory Server
- Multi-turn conversation with personalized fitness advice

## Running

```bash
cd examples/fitness_coach_mcp
pip install -r requirements.txt
python main.py
```

## Architecture

The fitness coach stores workout preferences and history in long-term memory via MCP. Each session is backed by Redis, so the agent can be restarted without losing conversation context.

See the [full source on GitHub](https://github.com/redis-developer/adk-redis/tree/main/examples/fitness_coach_mcp).
