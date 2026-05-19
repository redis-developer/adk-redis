# Search

`adk-redis` provides RedisVL-backed search tools that ADK agents can call during reasoning.

## How it works

The search tools use RedisVL to perform vector similarity search over a Redis index:

1. The agent decides it needs to search for information
2. It calls the search tool with a natural language query
3. The tool generates an embedding for the query
4. RedisVL performs a vector similarity search against the index
5. The top results are returned to the agent as context

## Available tools

| Tool | Description |
|------|-------------|
| `redis_vector_search` | Semantic search over a Redis vector index |
| `redis_hybrid_search` | Combined vector + keyword search (native FT.HYBRID on Redis 8.4+, aggregation fallback elsewhere) |
| `redis_range_search` | Vector search with a distance threshold |
| `redis_text_search` | Keyword full-text search via BM25 |
| `redis_sql_search` | SQL `SELECT` against a bound index via `redisvl.query.SQLQuery`. Requires the `adk-redis[sql]` extra. |

In addition to the in-process Python tools, you can connect an agent to RedisVL's own MCP server (one index per server) with `create_redisvl_mcp_toolset(...)`. The server exposes schema-aware `search-records` and `upsert-records` tools and is useful when the same index needs to be served to multiple agents or non-Python clients. See the [search tools how-to](../user_guide/how_to_guides/search_tools.md) for the decision matrix.

## Indexing

Before search tools can be used, documents must be indexed in Redis using RedisVL:

```python
from redisvl.index import SearchIndex

index = SearchIndex.from_yaml("schema.yaml")
index.create(overwrite=True)
index.load(documents)
```

## Relationship to RedisVL

The search tools are thin wrappers around RedisVL query types (`VectorQuery`, `FilterQuery`). They translate the agent's natural language query into a structured RedisVL search.
