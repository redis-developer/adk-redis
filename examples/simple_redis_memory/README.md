# Redis Memory Sample

This sample demonstrates the **complete two-tier memory architecture** using Redis Agent Memory Server with the `adk-redis` package:

1. **RedisWorkingMemorySessionService** - Session management with auto-summarization
2. **RedisLongTermMemoryService** - Persistent long-term memory with semantic search

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                          ADK Agent                             │
├──────────────────────────────┬─────────────────────────────────┤
│     TIER 1: Working Memory   │    TIER 2: Long-Term Memory     │
├──────────────────────────────┼─────────────────────────────────┤
│ • Current session messages   │ • Extracted facts & preferences │
│ • Auto-summarization         │ • Semantic vector search        │
│ • Context window management  │ • Cross-session persistence     │
│ • TTL support                │ • Recency-boosted retrieval     │
├──────────────────────────────┴─────────────────────────────────┤
│                    Agent Memory Server API                     │
├────────────────────────────────────────────────────────────────┤
│                         Redis Stack                            │
└────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- Docker (for Redis Stack and Agent Memory Server)

## Setup

### 1. Install adk-redis with web dependencies

```bash
pip install "adk-redis[web]"
```

Or install dependencies manually:

```bash
pip install adk-redis fastapi uvicorn python-dotenv httpx
```

### 2. Start Redis Stack

```bash
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest
```

### 3. Start Agent Memory Server

```bash
docker run -d --name agent-memory-server -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e OPENAI_API_KEY=your-openai-key \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

> **Note**: The memory server requires an OpenAI API key for embeddings by default. See the [Agent Memory Server docs](https://redis.github.io/agent-memory-server/) for alternative embedding providers.

### 4. Verify Setup

```bash
curl http://localhost:8000/health
```

### 5. Configure Environment

Create `.env` in this directory:

```bash
GOOGLE_API_KEY=your-google-api-key
REDIS_MEMORY_SERVER_URL=http://localhost:8000
REDIS_MEMORY_NAMESPACE=adk_agent_memory
REDIS_MEMORY_EXTRACTION_STRATEGY=discrete
REDIS_MEMORY_CONTEXT_WINDOW=8000
REDIS_MEMORY_RECENCY_BOOST=true
```

## Usage

```bash
cd examples/simple_redis_memory.py
python main.py
```

Open http://localhost:8080 in your browser.

## Demo Script

Run the interactive demo to see memory in action:

```bash
python demo_conversation.py
```

This will:
1. Create a session and share personal information
2. Wait for memory extraction
3. Create a NEW session and test memory recall

## Test Conversation

**Session 1** - Share information:
```
User: Hi, I'm Nitin. I'm a Machine Learning Engineer working on ML projects.
User: I love coffee, especially Berliner Frühstück Coffee from Berliner Kaffeerösterei. 
User: My favorite programming language is Python.
```

**Session 2** - Test memory recall:
```
User: What do you remember about me?
User: What's my favorite coffee?
```

## Features

| Feature | Working Memory (Tier 1) | Long-Term Memory (Tier 2) |
|---------|------------------------|---------------------------|
| Scope | Current session | All sessions |
| Auto-summarization | Yes | No |
| Semantic search | No | Yes |
| Fact extraction | Background | Persistent |
| TTL support | Yes | No |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_MEMORY_SERVER_URL` | `http://localhost:8000` | Memory server URL |
| `REDIS_MEMORY_NAMESPACE` | `adk_agent_memory` | Namespace for isolation |
| `REDIS_MEMORY_EXTRACTION_STRATEGY` | `discrete` | `discrete`, `summary`, `preferences` |
| `REDIS_MEMORY_CONTEXT_WINDOW` | `8000` | Max tokens before summarization |
| `REDIS_MEMORY_RECENCY_BOOST` | `true` | Boost recent memories in search |
