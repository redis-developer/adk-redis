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

### Development Mode (Single Container)

Runs API server with asyncio task backend (no separate worker needed):

```bash
docker run -d --name agent-memory-server \
  -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e OPENAI_API_KEY=your-openai-key \
  -e DISABLE_AUTH=true \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

### Production Mode (API + Worker)

Runs separate containers for API and background task worker:

**API Server:**
```bash
docker run -d --name agent-memory-api \
  -p 8000:8000 \
  -e REDIS_URL=redis://your-redis:6379 \
  -e OPENAI_API_KEY=your-openai-key \
  -e DISABLE_AUTH=false \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000
```

**Background Worker:**
```bash
docker run -d --name agent-memory-worker \
  -e REDIS_URL=redis://your-redis:6379 \
  -e OPENAI_API_KEY=your-openai-key \
  redislabs/agent-memory-server:latest \
  agent-memory task-worker --concurrency 10
```

### Using Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
      - "8001:8001"

  agent-memory-api:
    image: redislabs/agent-memory-server:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DISABLE_AUTH=true
    command: agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
    depends_on:
      - redis
```

Run:
```bash
export OPENAI_API_KEY=your-key
docker compose up -d
```

---

## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` (or `redis://host.docker.internal:6379` for Docker on Mac/Windows, `redis://172.17.0.1:6379` for Linux) |
| `OPENAI_API_KEY` | OpenAI API key (default provider) | `sk-...` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISABLE_AUTH` | `false` | Disable authentication (dev only) |
| `GENERATION_MODEL` | `gpt-4o` | LLM model for summarization |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `REDISVL_VECTOR_DIMENSIONS` | `1536` | Embedding dimensions |

### Alternative LLM Providers

**Anthropic:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GENERATION_MODEL=claude-3-5-sonnet-20241022
export EMBEDDING_MODEL=text-embedding-3-small  # Still use OpenAI for embeddings
```

**AWS Bedrock:**
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION_NAME=us-east-1
export GENERATION_MODEL=anthropic.claude-sonnet-4-5-20250929-v1:0
export EMBEDDING_MODEL=bedrock/amazon.titan-embed-text-v2:0
```

**Ollama (local):**
```bash
export OLLAMA_API_BASE=http://localhost:11434
export GENERATION_MODEL=ollama/llama2
export EMBEDDING_MODEL=ollama/nomic-embed-text
export REDISVL_VECTOR_DIMENSIONS=768  # Required for Ollama
```

**See:** https://redis.github.io/agent-memory-server/llm-providers/ for complete provider list

---

## Verification

### Health Check

```bash
curl http://localhost:8000/health
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
- Verify `OPENAI_API_KEY` is set correctly
- Check API key has sufficient credits
- Try alternative provider (Anthropic, Bedrock, Ollama)

### Memory Not Persisting

**Problem:** Memories disappear after restart

**Solution:**
- Verify Redis has persistence enabled
- Check Redis data directory is mounted as volume
- Ensure `REDIS_URL` points to correct Redis instance

