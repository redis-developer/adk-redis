# Travel Agent (Hybrid Memory)

A travel planning agent using both session-scoped memory and long-term persistent memory.

## What it demonstrates

- `RedisSessionService` for conversation state
- `RedisMemoryService` for long-term user preferences
- Hybrid memory pattern: session + persistent

## Running

```bash
cd examples/travel_agent_memory_hybrid
pip install -r requirements.txt
python main.py
```

## How it works

1. The agent starts a session and loads the user's travel preferences from long-term memory
2. During the conversation, it plans trips based on preferences and real-time input
3. At session end, new preferences are extracted and stored in long-term memory

See the [full source on GitHub](https://github.com/redis-developer/adk-redis/tree/main/examples/travel_agent_memory_hybrid).
