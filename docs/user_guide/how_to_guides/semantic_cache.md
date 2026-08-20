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

By default the provider creates the cache index, which needs `FT.CREATE` plus
an `FT.INFO` probe to detect an existing one. Where a platform team
provisions the index out of band and the agent credential is denied index
management, set `create_index=False` to attach to it instead. Requires
`redisvl>=0.26.0`.

```python
provider = RedisVLCacheProvider(
    config=RedisVLCacheProviderConfig(
        redis_url="redis://cache-user:password@redis.internal:6379",
        name="my_cache",  # must match the pre-provisioned index
        ttl=3600,
        distance_threshold=0.1,
        create_index=False,
    ),
    vectorizer=vectorizer,
)
```

#### Provisioning the index

RedisVL derives the schema from the cache name and the vectorizer. For
`name="my_cache"` over a 768 dimension vectorizer, provision the equivalent
of:

```
FT.CREATE my_cache ON HASH PREFIX 1 my_cache SCHEMA
  prompt TEXT response TEXT inserted_at NUMERIC updated_at NUMERIC
  prompt_vector VECTOR FLAT 6 TYPE FLOAT32 DIM 768 DISTANCE_METRIC COSINE
```

The index prefix is the bare name while entry keys are `my_cache:<entry_id>`.
So a credential's key pattern must cover `my_cache*`, not `my_cache:*`, and a
second cache whose name extends this one, such as `my_cache_v2`, is covered by
this index and returns the other cache's entries as hits. Give each cache a
name that is not a prefix of another.

!!! warning "The attached index is not validated"

    RedisVL checks nothing about an index it did not create (verified on
    redisvl 0.26.0). Which mismatches are loud depends on the field:

    - Wrong or absent `name`: `check()` raises `RedisSearchError` on the
      first lookup.
    - Wrong vector dimensions, key prefix, storage type, or distance
      metric: silent. Entries are written and TTLs set, every lookup
      misses, and the cache stops saving model calls without erroring.

    Confirm the index with `FT.INFO <name>` from a credential allowed to run
    it before deploying.

#### Minimum ACL

Measured on Redis 8.4, where `FT.SEARCH` carries both `@read` and `@search`
while `FT.CREATE` and `FT.INFO` carry only `@search`. So
`+@read +@write ~my_cache*` covers the entire runtime path and only index
creation needs `@search`: `store()` issues `HSET` and `EXPIRE`, `check()`
issues `FT.SEARCH` plus one `EXPIRE` per hit to refresh its TTL,
`delete_by_id()` issues `UNLINK`, and `clear()` scans the key prefix and
deletes. Three caveats:

- Because `check()` refreshes TTLs, the read path needs `@write` too. A
  read-only credential fails on lookup, not just on write.
- On Redis Open Source 7.x with the RediSearch module, and on Redis Software
  or Redis Cloud databases earlier than 8.2, module commands belong to no
  category, so the grant must name the command: `+@read +@write +FT.SEARCH`.
- A `redis_url` naming a non-zero database also needs `+SELECT`, which is in
  `@connection`. Keep the cache on database 0 or grant it explicitly.

An ACL that revokes search explicitly, `+@read +@write -@search`, loses
`FT.SEARCH` as well: entries still store, but every lookup fails and the
cache never serves a hit.

#### Seeing failures while developing

A cache backend failure is logged and the turn proceeds, so a broken cache
costs latency rather than breaking the agent. That also means a
misconfiguration can read as "caching just isn't working". While developing,
set `ignore_errors=False` to raise instead:

```python
llm_cache = LLMResponseCache(
    provider=provider,
    config=LLMResponseCacheConfig(ignore_errors=False),
)
```

Misconfiguration is still loud by default: a bad `redis_url`, a schema
mismatch, a denied `FT.INFO`, or a too-old redisvl all raise when the
provider is constructed. Only runtime lookup and store failures are
absorbed. To turn up the logs instead, raise the verbosity of the
`adk_redis.cache` logger.

#### Clearing entries

RedisVL refuses `clear()` and `delete()` on an index it does not manage, so
`clear()` deletes entries by scanning the `<name>:` key prefix instead. It
issues no index command and never drops the index; `delete_by_id()` is
unaffected. Neither is a barrier, because `SCAN` takes no snapshot, so an
entry written concurrently may survive a `clear()`.

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
| `distance_threshold` | Both | `0.1` (RedisVL), `None` (LangCache) | Max vector distance for a cache hit (lower = stricter). LangCache applies its server-side default when unset |
| `ttl` | Both | `3600` (RedisVL), `None` (LangCache) | Time-to-live in seconds for cache entries |
| `name` | RedisVL | `adk_semantic_cache` | Redis index name |
| `redis_url` | RedisVL | `redis://localhost:6379` | Redis connection string |
| `create_index` | RedisVL | `True` | Whether RedisVL creates and validates the index. `False` attaches to a pre-provisioned index and issues no index command. Requires `redisvl>=0.26.0` |
| `overwrite` | RedisVL | `False` | Whether to drop and recreate an existing index. Cannot be combined with `create_index=False` |
| `cache_id` | LangCache | Required | LangCache instance identifier |
| `api_key` | LangCache | Required | LangCache API key |
| `first_message_only` | Cache config | `True` | Only cache the first message per session |
| `ignore_errors` | Cache config | `True` | Log cache backend failures and carry on. Set `False` while developing to raise instead |
