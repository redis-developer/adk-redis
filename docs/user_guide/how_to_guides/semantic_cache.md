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

### Attaching to a pre-provisioned index

By default the provider creates the cache index, which requires `FT.CREATE`
and an `FT.INFO` probe to detect an existing index. Some deployments cannot
do that from the application: a platform team provisions the index out of
band, and the credential the agent runs under is denied index management.
Set `create_index=False` to attach to that index instead of creating it.

```python
provider = RedisVLCacheProvider(
    config=RedisVLCacheProviderConfig(
        redis_url="redis://cache-user:password@redis.internal:6379",
        name="my_cache",  # must match the pre-provisioned index name
        ttl=3600,
        distance_threshold=0.1,
        create_index=False,
    ),
    vectorizer=vectorizer,
)
```

Requires `redisvl>=0.26.0`. On older releases the provider raises an
`ImportError` naming the required version. Leaving `create_index=True`, the
default, keeps working on any supported `redisvl`.

With `create_index=False` the provider issues no index command while being
constructed, and RedisVL validates nothing about the index it attaches to.
The index must already exist under the same name and key prefix, over the
same storage type, with a vector field matching the vectorizer's dimensions.
A mismatch is not reported: queries return no results instead of failing, so
the cache silently misses on every prompt. Verify the index yourself with
`FT.INFO <name>` from a credential that is allowed to run it.

`create_index=False` cannot be combined with `overwrite=True`, because
overwrite means drop and recreate. The provider rejects that combination with
a `ValueError` before contacting Redis.

#### Minimum ACL for the runtime path

Measured on Redis 8.4. `FT.SEARCH` carries both the `@read` and `@search`
categories, while `FT.CREATE` and `FT.INFO` carry only `@search`. So a
`+@read +@write` grant is enough for the whole cache runtime path, and it is
exactly the grant that makes the default `create_index=True` path fail.

| Provider call | Redis commands | Allowed by `+@read +@write` |
|---------------|----------------|-----------------------------|
| Construction, `create_index=True` | `FT.INFO`, `FT.CREATE` | No |
| Construction, `create_index=False` | none | Yes |
| `store()` | `HSET`, `EXPIRE` | Yes |
| `check()` | `FT.SEARCH` | Yes |
| `delete_by_id()` | `DEL` | Yes |
| `clear()` | `SCAN`, `DEL` | Yes |

An ACL that revokes search explicitly, such as `+@read +@write -@search`,
also removes `FT.SEARCH`. That credential can still write entries, but
`check()` raises `RedisSearchError` and the cache never serves a hit, so it
adds latency without saving any model calls. `create_index=False` removes the
index management commands from the requirements, not the query itself.

#### Index-wide destructive calls

RedisVL refuses `clear()` and `delete()` on its extensions when
`create_index=False`, because it does not own the index lifecycle.
`RedisVLCacheProvider.clear()` handles that case by scanning the cache key
prefix and deleting the entry keys directly, so it needs no index command and
leaves the externally provisioned index in place. `delete_by_id()` deletes a
single key and is unaffected. adk-redis never drops the index.

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
| `ttl` | Both | `3600` (RedisVL), `None` (LangCache) | Time-to-live in seconds for cache entries |
| `name` | RedisVL | `adk_semantic_cache` | Redis index name |
| `redis_url` | RedisVL | `redis://localhost:6379` | Redis connection string |
| `create_index` | RedisVL | `True` | Whether RedisVL creates and validates the index. `False` attaches to a pre-provisioned index and issues no index command. Requires `redisvl>=0.26.0` |
| `overwrite` | RedisVL | `False` | Whether to drop and recreate an existing index. Cannot be combined with `create_index=False` |
| `cache_id` | LangCache | Required | LangCache instance identifier |
| `api_key` | LangCache | Required | LangCache API key |
| `first_message_only` | Cache config | `True` | Only cache the first message per session |
