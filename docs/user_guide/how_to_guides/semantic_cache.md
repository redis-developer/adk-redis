# Semantic Cache

This guide shows how to add semantic caching to a Google ADK agent so that
near-duplicate prompts return a cached LLM response instead of making a new
call.

For the concepts behind semantic caching, see
[Semantic Caching](../../concepts/caching.md).

## Option A: Self-hosted with RedisVL

Use `RedisVLCacheProvider` when you run your own Redis instance and want full
control over the vectorizer and cache index.

### Prerequisites

- Redis 8.4+ running locally (see [Redis setup](redis_setup.md)).
- `pip install 'adk-redis[search]'`

### Setup

```python
from google.adk import Agent
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis import (
    LLMResponseCache,
    LLMResponseCacheConfig,
    RedisVLCacheProvider,
    RedisVLCacheProviderConfig,
    create_llm_cache_callbacks,
)

# 1. Create a vectorizer (runs locally, no API key needed)
vectorizer = HFTextVectorizer(model="redis/langcache-embed-v1")

# 2. Create the cache provider
provider = RedisVLCacheProvider(
    config=RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379",
        name="my_cache",
        ttl=3600,
        distance_threshold=0.1,
    ),
    vectorizer=vectorizer,
)

# 3. Create the cache and wire callbacks into the agent
llm_cache = LLMResponseCache(
    provider=provider,
    config=LLMResponseCacheConfig(first_message_only=True),
)
before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

agent = Agent(
    model="gemini-2.0-flash",
    name="cached_agent",
    before_model_callback=before_cb,
    after_model_callback=after_cb,
)
```

See the
[semantic_cache example](https://github.com/redis-developer/adk-redis/tree/main/examples/semantic_cache)
for a runnable version.

---

## Option B: Managed with LangCache

Use `LangCacheProvider` with
[Redis LangCache](https://redis.io/langcache) for a fully managed service. No
local vectorizer or Redis instance needed; embeddings are handled server-side.

### Prerequisites

- A LangCache account and cache ID (sign up at
  [redis.io/langcache](https://redis.io/langcache)).
- `pip install 'adk-redis[langcache]'`

### Setup

```python
from google.adk import Agent

from adk_redis import (
    LLMResponseCache,
    LLMResponseCacheConfig,
    LangCacheProvider,
    LangCacheProviderConfig,
    create_llm_cache_callbacks,
)

provider = LangCacheProvider(
    config=LangCacheProviderConfig(
        cache_id="your-cache-id",
        api_key="your-api-key",
        server_url="https://aws-us-east-1.langcache.redis.io",
        ttl=3600,
    ),
)

llm_cache = LLMResponseCache(
    provider=provider,
    config=LLMResponseCacheConfig(first_message_only=False),
)
before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

agent = Agent(
    model="gemini-2.0-flash",
    name="langcache_agent",
    before_model_callback=before_cb,
    after_model_callback=after_cb,
)
```

See the
[langcache_cache example](https://github.com/redis-developer/adk-redis/tree/main/examples/langcache_cache)
for a runnable version.

---

## Configuration options

| Option | Provider | Default | Description |
|--------|----------|---------|-------------|
| `distance_threshold` | Both | `0.1` | Max vector distance for a cache hit (lower = stricter) |
| `ttl` | Both | `None` | Time-to-live in seconds for cache entries |
| `name` | RedisVL | `llmcache` | Redis index name |
| `redis_url` | RedisVL | `redis://localhost:6379` | Redis connection string |
| `cache_id` | LangCache | Required | LangCache instance identifier |
| `api_key` | LangCache | Required | LangCache API key |
| `first_message_only` | Cache config | `True` | Only cache the first message per session |
