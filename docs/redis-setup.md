# Redis Setup Guide

This guide covers Redis deployment options for use with adk-redis.

## Deployment Options

### Option 1: Redis Stack (Docker)

**Use case:** Local development with search tools (RedisVL integration)

**Features:**
- Redis with Search & Query modules
- JSON support
- RedisInsight GUI on port 8001

**Installation:**
```bash
docker run -d --name redis-stack \
  -p 6379:6379 \
  -p 8001:8001 \
  redis/redis-stack:latest
```

**Connection URL:**
```
redis://localhost:6379
```

**Verification:**
```bash
# Check container status
docker ps | grep redis-stack

# Test connection
redis-cli ping
# Expected: PONG

# Verify Search module
redis-cli FT._LIST
# Expected: (empty array) or list of indices
```

**Ports:**
- `6379`: Redis server
- `8001`: RedisInsight GUI (http://localhost:8001)

**Environment variables:** None required

**Stop/Remove:**
```bash
docker stop redis-stack
docker rm redis-stack
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
  -e OPENAI_API_KEY=your-openai-key \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

**Connection URL:**
```
http://localhost:8000
```

**Verification:**
```bash
# Health check
curl http://localhost:8000/health
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
- `OPENAI_API_KEY`: OpenAI API key for embeddings (or configure alternative provider)

**Optional environment variables:**
- `DISABLE_AUTH=true`: Disable authentication (development only)
- `GENERATION_MODEL=gpt-4o`: LLM model for summarization
- `EMBEDDING_MODEL=text-embedding-3-small`: Embedding model

**Stop/Remove:**
```bash
docker stop agent-memory-server
docker rm agent-memory-server
```

**See:** [Agent Memory Server Setup Guide](agent-memory-server-setup.md) for detailed configuration

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
| Redis Stack | ✅ | ✅ (via Agent Memory Server) | Local development |
| Redis Cloud | ✅ | ✅ (via Agent Memory Server) | Production |
| Redis Enterprise | ✅ | ✅ (via Agent Memory Server) | Enterprise production |
| Redis Sentinel | ✅ | ✅ (via Agent Memory Server) | High availability |

**Note:** Memory services require both a Redis deployment AND Agent Memory Server. Search tools only need Redis with Search module.

