# Search Tools

This guide shows how to add RedisVL-backed search tools to a Google ADK agent.

## Prerequisites

- Redis running with indexed documents
- `adk-redis` installed: `pip install adk-redis`
- RedisVL index created and populated

## Adding search tools

```python
from google.adk.agents import Agent
from adk_redis.tools import create_redis_search_tool

# Create a search tool backed by RedisVL
search_tool = create_redis_search_tool(
    redis_url="redis://localhost:6379",
    index_name="my_docs",
    description="Search internal documentation for relevant information",
)

# Add the tool to your ADK agent
agent = Agent(
    model="gemini-2.0-flash",
    name="search_agent",
    instruction="You are a helpful assistant. Use the search tool to find relevant documents.",
    tools=[search_tool],
)
```

## How it works

1. The agent decides it needs to search for information
2. ADK calls the search tool with the agent's query
3. The tool generates an embedding and searches the RedisVL index
4. Top results are returned as context for the agent's response

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `redis_url` | Required | Redis connection string |
| `index_name` | Required | RedisVL index name |
| `top_k` | `5` | Number of results to return |
| `vector_field` | `embedding` | Name of the vector field in the index |
