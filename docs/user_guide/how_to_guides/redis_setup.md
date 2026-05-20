# Redis Setup Guide

> **See also:** [ADK + Redis on redis.io](https://redis.io/docs/latest/integrate/google-adk/) for additional coverage.

This guide covers Redis deployment options for use with adk-redis.

## Deployment Options

### Option 1: Redis 8.4+ (Docker)

**Use case:** Recommended for all new projects. Redis 8.4 includes the Redis
Query Engine (vector search, full-text search, JSON) with no extra modules.

**Installation:**
```bash
docker run -d --name redis -p 6379:6379 redis:8.4-alpine
```

**Connection URL:**
```
redis://localhost:6379
```

**Verification:**
```bash
# Test connection
redis-cli ping
# Expected: PONG

# Verify Search engine
redis-cli FT._LIST
# Expected: (empty array) or list of indices
```

**Stop/Remove:**
```bash
docker stop redis
docker rm redis
```

---

### Option 2: Redis Agent Memory Server (Docker)

**Use case:** Memory and session services (RedisLongTermMemoryService, RedisWorkingMemorySessionService)

**Features:**
- Two-tier memory architecture (working + long-term)
- Automatic memory extraction
- Semantic search with recency boosting
- Auto-summarization

**Installation:**
```bash
# Development mode (single container, asyncio backend)
docker run -d --name agent-memory-server \
  -p 8000:8000 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  -e DISABLE_AUTH=true \
  redislabs/agent-memory-server:0.13.2 \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

**Connection URL:**
```
http://localhost:8000
```

**Verification:**
```bash
# Health check
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy"}

# API docs (open in browser)
# http://localhost:8000/docs
```

**Ports:**
- `8000`: HTTP API server

**Required environment variables:**
- `REDIS_URL`: Redis connection string
    - Mac/Windows: `redis://host.docker.internal:6379`
    - Linux: `redis://172.17.0.1:6379` or use `--network host`
- LLM provider API key (e.g. `GEMINI_API_KEY`, `OPENAI_API_KEY`)

**Optional environment variables:**
- `DISABLE_AUTH=true`: Disable authentication (development only)
- `GENERATION_MODEL`: LLM model for summarization (e.g. `gemini/gemini-2.0-flash-exp`)
- `EMBEDDING_MODEL`: Embedding model (e.g. `gemini/text-embedding-004`)

**Stop/Remove:**
```bash
docker stop agent-memory-server
docker rm agent-memory-server
```

**See:** [Agent Memory Server Setup Guide](memory_server_setup.md) for detailed configuration

---

### Option 3: Redis Cloud

**Use case:** Managed production deployment with free tier

**Features:**
- Fully managed Redis with Search & Query
- Free tier: 30MB storage
- Automatic backups and high availability

**Setup:**
1. Sign up at https://redis.io/try-free
2. Create database with "Search and Query" capability
3. Copy connection details from dashboard

**Connection URL format:**
```
redis://default:password@redis-12345.c123.us-east-1-1.ec2.redns.redis-cloud.com:12345
```

**Verification:**
```bash
# Test connection (replace with your URL)
redis-cli -u "redis://default:password@your-host:port" ping
```

**Environment variables:**
```bash
export REDIS_URL="redis://default:password@your-host:port"
```

---

### Option 4: Redis Enterprise

**Use case:** Self-hosted commercial deployment for production

**Features:**
- Active-Active geo-distribution
- Auto-tiering (RAM + Flash)
- 99.999% uptime SLA
- Enterprise support

**Setup:** See https://redis.io/enterprise/

**Connection URL format:**
```
redis://username:password@your-enterprise-host:port
```

---

### Option 5: Redis Sentinel

**Use case:** High availability with automatic failover

**Features:**
- Automatic failover
- Monitoring and notifications
- Configuration provider for clients

**Connection URL format:**
```
redis+sentinel://sentinel1:26379,sentinel2:26379/mymaster
```

**Setup:** See https://redis.io/docs/management/sentinel/

---

## Feature Compatibility

| Redis Deployment | Search Tools | Memory Services Backend | Use Case |
|------------------|--------------|-------------------------|----------|
| Redis 8.4+ | ✅ | ✅ (via Agent Memory Server) | Recommended for all new projects |
| Redis Cloud | ✅ | ✅ (via Agent Memory Server) | Managed production |
| Redis Enterprise | ✅ | ✅ (via Agent Memory Server) | Enterprise production |
| Redis Sentinel | ✅ | ✅ (via Agent Memory Server) | High availability |

**Note:** Memory services require both a Redis deployment AND Agent Memory Server. Search tools only need Redis with the Query Engine.

