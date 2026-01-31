# Agent Memory Server Setup Guide

Complete setup instructions for Redis Agent Memory Server.

## Overview

Agent Memory Server provides:
- Two-tier memory architecture (working memory + long-term memory)
- Automatic memory extraction from conversations
- Semantic search with vector embeddings
- Auto-summarization when context window limits exceeded
- Background task processing for memory promotion

**Repository:** https://github.com/redis/agent-memory-server

---

## Installation

> **Important**: A recent bug fix for non-OpenAI provider support is available in the latest GitHub commit but not yet in a release. Build from source to use the fix.

### Prerequisites

- Docker installed
- Git installed
- Redis 8.4+ running (see [Redis Setup Guide](redis-setup.md))

### Build from Source

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

> **Using the official release**: Once the next version is released, you can use `redislabs/agent-memory-server:latest` instead of building from source.

### Development Mode (Single Container)

Runs API server with asyncio task backend (no separate worker needed):

```bash
docker run -d --name agent-memory-server \
  -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  -e DISABLE_AUTH=true \
  agent-memory-server:latest-fix \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

### Production Mode (API + Worker)

Runs separate containers for API and background task worker:

**API Server:**
```bash
docker run -d --name agent-memory-api \
  -p 8000:8000 \
  -e REDIS_URL=redis://your-redis:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  -e DISABLE_AUTH=false \
  agent-memory-server:latest-fix \
  agent-memory api --host 0.0.0.0 --port 8000
```

**Background Worker:**
```bash
docker run -d --name agent-memory-worker \
  -e REDIS_URL=redis://your-redis:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  agent-memory-server:latest-fix \
  agent-memory task-worker --concurrency 10
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:8.4-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  agent-memory-api:
    image: agent-memory-server:latest-fix
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GENERATION_MODEL=gemini/gemini-2.0-flash-exp
      - EMBEDDING_MODEL=gemini/text-embedding-004
      - EXTRACTION_DEBOUNCE_SECONDS=5
      - DISABLE_AUTH=true
    command: agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
    depends_on:
      redis:
        condition: service_healthy
```

Run:
```bash
export GEMINI_API_KEY=your-key
docker compose up -d
```

---

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` (or `redis://host.docker.internal:6379` for Docker on Mac/Windows, `redis://172.17.0.1:6379` for Linux) |
| LLM Provider API Key | API key for your chosen provider | `GEMINI_API_KEY=...`, `OPENAI_API_KEY=...`, `ANTHROPIC_API_KEY=...`, etc. |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISABLE_AUTH` | `false` | Disable authentication (dev only) |
| `GENERATION_MODEL` | `gpt-5` | LLM model for summarization and memory extraction |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for semantic search |
| `REDISVL_VECTOR_DIMENSIONS` | `1536` | Embedding dimensions (required for some models like Ollama) |
| `EXTRACTION_DEBOUNCE_SECONDS` | `300` | Debounce period (in seconds) for memory extraction. Lower values (e.g., 5) provide faster memory extraction, while higher values reduce API calls |

### LLM Provider Configuration

Agent Memory Server uses [LiteLLM](https://docs.litellm.ai/) and supports 100+ providers. Set the appropriate environment variables for your provider:

**Google Gemini:**
```bash
export GEMINI_API_KEY=your-key
export GENERATION_MODEL=gemini/gemini-2.0-flash-exp
export EMBEDDING_MODEL=gemini/text-embedding-004
```

**OpenAI:**
```bash
export OPENAI_API_KEY=sk-...
export GENERATION_MODEL=gpt-4o
export EMBEDDING_MODEL=text-embedding-3-small
```

**Anthropic:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GENERATION_MODEL=claude-3-5-sonnet-20241022
export EMBEDDING_MODEL=gemini/text-embedding-004  # Use Gemini for embeddings
export GEMINI_API_KEY=your-gemini-key
```

**AWS Bedrock:**
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION_NAME=us-east-1
export GENERATION_MODEL=anthropic.claude-sonnet-4-5-20250929-v1:0
export EMBEDDING_MODEL=bedrock/amazon.titan-embed-text-v2:0
```

**Ollama (local/offline):**
```bash
export OLLAMA_API_BASE=http://localhost:11434
export GENERATION_MODEL=ollama/llama2
export EMBEDDING_MODEL=ollama/nomic-embed-text
export REDISVL_VECTOR_DIMENSIONS=768  # Required for Ollama embeddings
```

**See the complete provider list:**
- **Generation Models**: https://redis.github.io/agent-memory-server/llm-providers/
- **Embedding Models**: https://redis.github.io/agent-memory-server/embedding-providers/

---

## Verification

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Expected response:
```json
{"status":"healthy"}
```

### API Documentation

View interactive API documentation at http://localhost:8000/docs

### Test Memory Operations

```bash
# Create a working memory session
curl -X POST http://localhost:8000/api/v1/working-memory \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "namespace": "test",
    "user_id": "user123",
    "messages": [
      {"role": "user", "content": "My name is Alice"}
    ]
  }'

# Search long-term memory
curl -X POST http://localhost:8000/api/v1/long-term-memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is my name?",
    "namespace": "test",
    "user_id": "user123"
  }'
```

---

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to Redis

**Solution:**
- Verify Redis is running: `docker ps | grep redis`
- Check `REDIS_URL` format: `redis://host:port`
- For Docker on Mac/Windows, use `host.docker.internal` instead of `localhost`

### Authentication Errors

**Problem:** 401 Unauthorized

**Solution:**
- Set `DISABLE_AUTH=true` for development
- For production, configure OAuth2/JWT (see https://redis.github.io/agent-memory-server/authentication/)

### Embedding Errors

**Problem:** "Invalid API key" or embedding failures

**Solution:**
- Verify your LLM provider API key is set correctly (e.g., `GEMINI_API_KEY`, `OPENAI_API_KEY`)
- Check API key has sufficient credits/quota
- Try alternative provider (Gemini, Anthropic, Bedrock, Ollama)
- For local/offline embeddings, use Ollama with `EMBEDDING_MODEL=ollama/nomic-embed-text` and `REDISVL_VECTOR_DIMENSIONS=768`

### Memory Not Persisting

**Problem:** Memories disappear after restart

**Solution:**
- Verify Redis has persistence enabled
- Check Redis data directory is mounted as volume
- Ensure `REDIS_URL` points to correct Redis instance

