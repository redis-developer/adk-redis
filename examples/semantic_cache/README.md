# Semantic Cache Sample

This sample demonstrates how to use semantic caching with ADK agents using
the community package. Semantic caching stores LLM responses and retrieves
them for semantically similar queries, reducing latency and API costs.

## Prerequisites

- Python 3.9+ (Python 3.11+ recommended)
- Redis server (local or cloud)
- ADK and adk-redis installed
- Google API key (for the LLM)

## Setup

### 1. Install Dependencies

```bash
pip install google-adk adk-redis
```

### 2. Start Redis

Using Docker:
```bash
docker run -d --name redis -p 6379:6379 redis:8.4-alpine
```

Or install Redis locally following the [Redis documentation](https://redis.io/docs/getting-started/).

> **Note**: Redis 8.4 includes the Redis Query Engine with native support for vector search and JSON operations.

### 3. Configure Environment Variables

Create a `.env` file in this directory (or copy from `.env.example`):

```bash
# Required: Google API key for the agent
GOOGLE_API_KEY=your-google-api-key

# Optional: Redis URL (defaults to redis://localhost:6379)
REDIS_URL=redis://localhost:6379
```

**Note**: This example uses the `redis/langcache-embed-v1` embedding model which runs locally and doesn't require an API key. RedisVL supports many other vectorizers including OpenAI, Cohere, HuggingFace, Mistral, and more. See the [RedisVL Vectorizers documentation](https://docs.redisvl.com/en/latest/user_guide/vectorizers.html) for all options.

## Usage

### Option 1: Run the Demo Script

```bash
uv run python main.py
```

This runs a demo that:
1. Creates an agent with semantic caching enabled
2. Sends multiple queries, including semantically similar ones
3. Shows cache hits for similar queries

### Option 2: Use with ADK Web

```bash
adk web .
```

Then open http://localhost:8000 to interact with the cached agent.

## Sample Structure

```
semantic_cache/
├── main.py                      # Demo script
├── semantic_cache_agent/
│   ├── __init__.py              # Agent package initialization
│   └── agent.py                 # Agent with caching callbacks
└── README.md                    # This file
```

## How It Works

1. **Before Model Callback**: Checks if a semantically similar prompt exists
   in the cache. If found, returns the cached response immediately.

2. **After Model Callback**: Stores the prompt-response pair in the cache
   for future similar queries.

3. **Semantic Similarity**: Uses vector embeddings to find similar prompts,
   not exact string matching. "What is Python?" and "Tell me about Python"
   would match.

## Configuration Options

### RedisVLCacheProviderConfig

- `redis_url` (str): Redis connection string
- `name` (str): Cache index name
- `ttl` (int): Time-to-live in seconds for cached entries
- `distance_threshold` (float): Semantic similarity threshold (0-2 for COSINE)

### LLMResponseCacheConfig

- `first_message_only` (bool): Only cache first message in session
- `include_app_name` (bool): Include app name in cache key
- `include_user_id` (bool): Include user ID in cache key
- `include_session_id` (bool): Include session ID in cache key

## Tool Caching

You can also cache tool results:

```python
from adk_redis.cache import (
    ToolCache,
    ToolCacheConfig,
    create_tool_cache_callbacks,
)

tool_cache = ToolCache(
    provider=provider,
    config=ToolCacheConfig(
        tool_names={"search_web", "get_weather"},  # Tools to cache
    ),
)

before_tool_cb, after_tool_cb = create_tool_cache_callbacks(tool_cache)

agent = Agent(
    name="my_agent",
    before_tool_callback=before_tool_cb,
    after_tool_callback=after_tool_cb,
)
```

## Learn More

- [ADK Documentation](https://google.github.io/adk-docs)
- [RedisVL Documentation](https://redis.io/docs/latest/integrate/redisvl/)
- [Redis Semantic Caching](https://redis.io/docs/latest/develop/interact/search-and-query/advanced-concepts/vectors/)

