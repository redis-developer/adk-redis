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
| `redis_hybrid_search` | Combined vector + keyword search |

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
