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
│                          Redis 8.4                             │
└────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10+
- Docker (for Redis 8.4 and Agent Memory Server)

## Setup

### 1. Install uv and dependencies

First, install [uv](https://docs.astral.sh/uv/) if you haven't already:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

Then install the package with all dependencies:

```bash
uv pip install "adk-redis[all]"
```

### 2. Start Redis 8.4

```bash
docker run -d --name redis -p 6379:6379 redis:8.4-alpine
```

> **Note**: Redis 8.4 includes the Redis Query Engine (evolved from RediSearch) with native support for vector search, full-text search, and JSON operations.

### 3. Build and Start Agent Memory Server

> **Important**: A recent bug fix for non-OpenAI provider support is available in the latest GitHub commit but not yet in a release. Build from source to use the fix.

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

**Start the server:**

```bash
docker run -d --name agent-memory-server -p 8088:8088 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e FAST_MODEL=gemini/gemini-2.0-flash \
  -e SLOW_MODEL=gemini/gemini-2.0-flash \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  agent-memory-server:latest-fix \
  agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
```

> **Configuration Options:**
> - **LLM Provider**: Agent Memory Server uses [LiteLLM](https://docs.litellm.ai/) and supports 100+ providers (OpenAI, Gemini, Anthropic, AWS Bedrock, Ollama, etc.). Set the appropriate environment variables for your provider (e.g., `GEMINI_API_KEY`, `GENERATION_MODEL=gemini/gemini-2.0-flash`). See the [Agent Memory Server LLM Providers docs](https://redis.github.io/agent-memory-server/llm-providers/) for details.
> - **Memory Extraction Debounce**: `EXTRACTION_DEBOUNCE_SECONDS` controls how long to wait before extracting memories from a conversation (default: 300 seconds). Lower values (e.g., 5) provide faster memory extraction, while higher values reduce API calls.
> - **Embedding Models**: Agent Memory Server also uses LiteLLM for embeddings. For local/offline embeddings, use Ollama (e.g., `EMBEDDING_MODEL=ollama/nomic-embed-text`, `REDISVL_VECTOR_DIMENSIONS=768`). Note: The `redis/langcache-embed-v1` model used in the semantic_cache example is not supported by Agent Memory Server (it's RedisVL-specific). See [Embedding Providers docs](https://redis.github.io/agent-memory-server/embedding-providers/) for all options.
>
> **Using the official release**: Once the next version is released, you can use `redislabs/agent-memory-server:latest` instead of building from source.

### 4. Verify Setup

```bash
curl http://localhost:8088/v1/health
```

### 5. Configure Environment

Create `.env` in this directory:

```bash
GOOGLE_API_KEY=your-google-api-key
REDIS_MEMORY_SERVER_URL=http://localhost:8088
REDIS_MEMORY_NAMESPACE=adk_agent_memory
REDIS_MEMORY_EXTRACTION_STRATEGY=discrete
REDIS_MEMORY_CONTEXT_WINDOW=8000
REDIS_MEMORY_RECENCY_BOOST=true
```

## Usage

Run the web server:

```bash
cd examples/simple_redis_memory
uv run python main.py
```

Open http://localhost:8080 in your browser.

> **Note**: This project uses `uv` for dependency management. If you prefer to use `pip`, install the package first: `uv pip install "adk-redis[all]"` and then run `python main.py`.

## Demo Script

Run the interactive demo to see memory in action:

```bash
uv run python demo_conversation.py
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
| `REDIS_MEMORY_SERVER_URL` | `http://localhost:8088` | Memory server URL |
| `REDIS_MEMORY_NAMESPACE` | `adk_agent_memory` | Namespace for isolation |
| `REDIS_MEMORY_EXTRACTION_STRATEGY` | `discrete` | `discrete`, `summary`, `preferences` |
| `REDIS_MEMORY_CONTEXT_WINDOW` | `8000` | Max tokens before summarization |
| `REDIS_MEMORY_RECENCY_BOOST` | `true` | Boost recent memories in search |
