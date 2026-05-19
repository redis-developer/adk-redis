# Search Tools

This guide shows how to add RedisVL-backed search tools to a Google ADK agent.

## Prerequisites

- Redis 8.4+ with the RediSearch module, or Redis Cloud with Search.
- `adk-redis` with the search extra: `pip install 'adk-redis[search]'`.
- A RedisVL index with the documents you want to search.

## In-process Python tools

All five tools subclass `BaseRedisSearchTool` and accept a bound RedisVL `SearchIndex` / `AsyncSearchIndex`.

### Vector search

```python
from google.adk import Agent
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis import RedisVectorQueryConfig, RedisVectorSearchTool

vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")
index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")

tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisVectorQueryConfig(
        vector_field_name="embedding",
        num_results=5,
    ),
    return_fields=["title", "price", "category"],
    name="search_products",
    description="Semantic search across the product catalog.",
)

agent = Agent(model="gemini-2.0-flash", tools=[tool])
```

### Hybrid search

Combines vector similarity with BM25 keyword scoring. On Redis 8.4+ with `redisvl>=0.18.2`, the tool uses the native `FT.HYBRID` command. On older versions or older Redis it falls back to client-side aggregation.

```python
from adk_redis import RedisHybridQueryConfig, RedisHybridSearchTool

tool = RedisHybridSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisHybridQueryConfig(
        text_field_name="description",
        combination_method="LINEAR",
        linear_alpha=0.7,  # 70% text, 30% vector
        num_results=10,
        stopwords=None,  # set to a language string when nltk is installed
    ),
)
```

### Range search

Returns every document within a distance threshold of the query vector.

```python
from adk_redis import RedisRangeQueryConfig, RedisRangeSearchTool

tool = RedisRangeSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisRangeQueryConfig(
        vector_field_name="embedding",
        distance_threshold=0.3,
        num_results=20,
    ),
)
```

### Text search

BM25-only keyword search. No vectorizer required.

```python
from adk_redis import RedisTextQueryConfig, RedisTextSearchTool

tool = RedisTextSearchTool(
    index=index,
    config=RedisTextQueryConfig(text_field_name="content"),
    return_fields=["title", "content"],
)
```

### SQL search

`RedisSQLSearchTool` wraps `redisvl.query.SQLQuery`. The LLM passes a SQL `SELECT` statement and an optional `params` object; the tool translates it into the right `FT.SEARCH` or `FT.AGGREGATE` call.

```python
from adk_redis import RedisSQLSearchTool

tool = RedisSQLSearchTool(
    index=index,
    sql_redis_options={"schema_cache_strategy": "lazy"},
)
```

Example SQL the agent might emit:

```sql
SELECT title, price, category
FROM products
WHERE category = 'electronics' AND price < :max_price
```

with `params={"max_price": 50}`. Install with `pip install 'adk-redis[sql]'`.

## RedisVL MCP toolset

`create_redisvl_mcp_toolset(...)` returns an ADK `McpToolset` that talks to RedisVL's own MCP server (`rvl mcp`). The server exposes two tools per index:

- `search-records`: schema-aware search with filter hints embedded in the tool description.
- `upsert-records`: write path. Suppress with `read_only=True` (the default for stdio mode).

```python
from pydantic import SecretStr
from adk_redis import create_redisvl_mcp_toolset

# Remote server (default transport is streamable-http).
toolset = create_redisvl_mcp_toolset(
    url="http://localhost:8000/mcp",
    auth_token=SecretStr("..."),  # optional bearer
)

# In-process stdio: spawn `rvl mcp --config <path>`.
toolset = create_redisvl_mcp_toolset(
    transport="stdio",
    config_path="/etc/redisvl/mcp.yaml",
    read_only=True,
)

agent = Agent(model="gemini-2.0-flash", tools=[toolset])
```

Install with `pip install 'adk-redis[mcp-search]'`. The server-side dependency is shipped by `redisvl[mcp]` and started with `rvl mcp --config <path> --transport streamable-http`.

## When to use which

| Path | Use when |
|---|---|
| In-process tools (`RedisVectorSearchTool`, etc.) | Single Python agent, fine-grained control, no extra service to operate. |
| `create_redisvl_mcp_toolset(...)` | Multiple agents (Python, JS, Claude Desktop) share one index, schema-aware tool descriptions, you want `--read-only` as a deployment-level guardrail. |

## Notes

- All in-process search tools accept custom `name` and `description` so the LLM sees a domain-specific tool.
- `epsilon` is a `VECTOR_RANGE`-only attribute, so `RedisVectorQueryConfig` does not accept it. Use `RedisRangeQueryConfig.epsilon` for range searches.
- The hybrid tool auto-detects native FT.HYBRID support. Pass a `RedisAggregatedHybridQueryConfig` explicitly to force the older aggregation path.
