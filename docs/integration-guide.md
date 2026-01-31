# Integration Guide

Complete guide for integrating Redis Agent Memory Server with adk-redis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         ADK Application                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      ADK Agent                           │   │
│  │  ┌────────────────────┐    ┌──────────────────────────┐  │   │
│  │  │ Session Service    │    │   Memory Service         │  │   │
│  │  │ (Working Memory)   │    │   (Long-Term Memory)     │  │   │
│  │  └────────┬───────────┘    └──────────┬───────────────┘  │   │
│  └───────────┼────────────────────────────┼──────────────────┘   │
└──────────────┼────────────────────────────┼──────────────────────┘
               │                            │
               │    HTTP API (port 8000)    │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Redis Agent Memory Server                          │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │  Working Memory API  │    │  Long-Term Memory API        │  │
│  │  - Session messages  │    │  - Semantic search           │  │
│  │  - Auto-summarize    │    │  - Memory extraction         │  │
│  │  - Context window    │    │  - Recency boosting          │  │
│  └──────────┬───────────┘    └──────────┬───────────────────┘  │
└─────────────┼────────────────────────────┼──────────────────────┘
              │                            │
              │    Redis Protocol          │
              ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Redis 8.4+                              │
│  - JSON storage                                                 │
│  - Vector search (Redis Query Engine)                           │
│  - Full-text search                                             │
│  - Persistence                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **ADK Agent** | Agent logic, tool execution, response generation |
| **adk-redis Session Service** | Implements ADK's `BaseSessionService` interface |
| **adk-redis Memory Service** | Implements ADK's `BaseMemoryService` interface |
| **Agent Memory Server** | Memory extraction, summarization, vector search |
| **Redis 8.4+** | Data storage, vector indexing, full-text search, persistence |

---

## Complete Setup

### 1. Start Infrastructure

> **Important**: A recent bug fix for non-OpenAI provider support is available in the latest GitHub commit but not yet in a release. Build Agent Memory Server from source first.

**Build Agent Memory Server from source:**

**Option A: Automated setup (recommended)**

```bash
# Run the setup script from the repository root
./scripts/setup-agent-memory-server.sh
```

This script will automatically clone, build, and verify the Agent Memory Server image.

**Option B: Manual setup**

```bash
# Clone the repository
git clone https://github.com/redis/agent-memory-server.git /tmp/agent-memory-server
cd /tmp/agent-memory-server

# Build Docker image
docker build -t agent-memory-server:latest-fix .
```

**Start the infrastructure:**

```bash
# Start Redis 8.4
docker run -d --name redis -p 6379:6379 redis:8.4-alpine

# Start Agent Memory Server
docker run -d --name agent-memory-server \
  -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=30 \
  -e DISABLE_AUTH=true \
  agent-memory-server:latest-fix \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio

# Verify
curl http://localhost:8000/v1/health
```

> **Note**: Redis 8.4 includes the Redis Query Engine (evolved from RediSearch) with native support for vector search, full-text search, and JSON operations. Redis Stack is no longer needed.

**Note:** On Linux, replace `host.docker.internal` with `172.17.0.1` or use `--network host` mode.

### 2. Install Dependencies

```bash
pip install google-adk "adk-redis[memory]"
```

### 3. Configure Services

```python
from google.adk import Agent
from google.adk.runners import Runner
from adk_redis.memory import RedisLongTermMemoryService, RedisLongTermMemoryServiceConfig
from adk_redis.sessions import RedisWorkingMemorySessionService, RedisWorkingMemorySessionServiceConfig

# Configure session service (Tier 1: Working Memory)
session_config = RedisWorkingMemorySessionServiceConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    model_name="gpt-4o",
    context_window_max=8000,
    extraction_strategy="discrete",
)
session_service = RedisWorkingMemorySessionService(config=session_config)

# Configure memory service (Tier 2: Long-Term Memory)
memory_config = RedisLongTermMemoryServiceConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    extraction_strategy="discrete",
    recency_boost=True,
    semantic_weight=0.8,
    recency_weight=0.2,
)
memory_service = RedisLongTermMemoryService(config=memory_config)

# Create agent
agent = Agent(
    name="memory_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant with long-term memory.",
)

# Create runner with both services
runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

---

## Configuration Reference

### RedisWorkingMemorySessionServiceConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_base_url` | `str` | `http://localhost:8000` | Agent Memory Server URL |
| `default_namespace` | `str` | `None` | Namespace for session isolation |
| `model_name` | `str` | `None` | LLM model for summarization |
| `context_window_max` | `int` | `None` | Max tokens before auto-summarization |
| `extraction_strategy` | `str` | `discrete` | `discrete`, `summary`, `preferences`, `custom` |
| `session_ttl_seconds` | `int` | `None` | Session expiration time |
| `timeout` | `float` | `30.0` | HTTP request timeout |

### RedisLongTermMemoryServiceConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_base_url` | `str` | `http://localhost:8000` | Agent Memory Server URL |
| `default_namespace` | `str` | `None` | Namespace for memory isolation |
| `search_top_k` | `int` | `10` | Max memories per search |
| `distance_threshold` | `float` | `None` | Max distance for search results (0.0-1.0) |
| `recency_boost` | `bool` | `True` | Enable recency-aware ranking |
| `semantic_weight` | `float` | `0.8` | Weight for semantic similarity (0.0-1.0) |
| `recency_weight` | `float` | `0.2` | Weight for recency score (0.0-1.0) |
| `extraction_strategy` | `str` | `discrete` | `discrete`, `summary`, `preferences`, `custom` |
| `timeout` | `float` | `30.0` | HTTP request timeout |

---

## Running Examples

### Memory Example

```bash
cd examples/simple_redis_memory
pip install "adk-redis[web]"

# Set environment
export GOOGLE_API_KEY=your-google-key
export REDIS_MEMORY_SERVER_URL=http://localhost:8000

# Run
python main.py
```

Open http://localhost:8080

**Test conversation:**
1. Session 1: "Hi, I'm Alice. I love pizza and Python programming."
2. Wait 5 seconds for memory extraction
3. Session 2 (new session): "What do you remember about me?"

### Search Tools Example

```bash
cd examples/redis_search_tools
pip install adk-redis

# Set environment
export REDIS_URL=redis://localhost:6379
export GOOGLE_API_KEY=your-google-key

# Load data
python load_data.py

# Run agent
adk web redis_search_tools_agent
```

---

## Data Flow

### Session Message Flow

```
1. User sends message
   ↓
2. ADK Agent processes with RedisWorkingMemorySessionService
   ↓
3. Session service stores message in Agent Memory Server (Working Memory API)
   ↓
4. Agent Memory Server stores in Redis
   ↓
5. Background task extracts memories to Long-Term Memory
```

### Memory Search Flow

```
1. ADK Agent needs context
   ↓
2. RedisLongTermMemoryService.search_memory() called
   ↓
3. Query sent to Agent Memory Server (Long-Term Memory API)
   ↓
4. Agent Memory Server performs vector search in Redis
   ↓
5. Results ranked with recency boosting
   ↓
6. Memories returned to agent
```

---

## Troubleshooting

### No memories found

**Cause:** Memory extraction hasn't completed

**Solution:** Wait 5-10 seconds after sending messages for background extraction

### Connection refused

**Cause:** Agent Memory Server not running

**Solution:**
```bash
docker ps | grep agent-memory-server
curl http://localhost:8000/v1/health
```

### Import errors

**Cause:** Missing dependencies

**Solution:**
```bash
pip install "adk-redis[memory]"
```

