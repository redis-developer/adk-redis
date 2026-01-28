# ADK-Redis

Redis integrations for Google's Agent Development Kit (ADK).

[![PyPI version](https://badge.fury.io/py/adk-redis.svg)](https://badge.fury.io/py/adk-redis)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/redis-applied-ai/adk-redis/workflows/CI/badge.svg)](https://github.com/redis-applied-ai/adk-redis/actions)

## Overview

`adk-redis` provides Redis-based implementations of ADK services and tools:

- **Memory Services**: Long-term agent memory with semantic search and automatic memory extraction
- **Session Services**: Working memory session management with auto-summarization
- **Search Tools**: Vector, hybrid, range, and text search tools for RAG applications

## Key Technologies

### Redis Agent Memory Server

The memory and session services integrate with the
[Redis Agent Memory Server](https://github.com/redis/agent-memory-server), an open-source
memory layer for AI agents that provides:

- **Two-Tier Memory Architecture**: Working memory (session-scoped) for current conversation
  context, and long-term memory (persistent) for facts, preferences, and knowledge
- **Automatic Memory Extraction**: LLM-based extraction of facts, preferences, and episodic
  memories from conversations
- **Semantic Search**: Vector-based similarity search with recency boosting
- **Auto-Summarization**: Automatic summarization when context window limits are exceeded
- **Background Processing**: Non-blocking memory promotion and indexing

### RedisVL (Redis Vector Library)

The search tools are built on [RedisVL](https://docs.redisvl.com/), the AI-native Python
client for Redis that provides:

- **Index Management**: Define and manage vector search indices with YAML or Python
- **Advanced Vector Search**: KNN and range-based vector queries with filtering
- **Hybrid Search**: Combine vector similarity with full-text search
- **Multiple Vectorizers**: Support for OpenAI, HuggingFace, Cohere, and more

## Installation

```bash
# Install base package
pip install adk-redis

# Install with memory service support (Redis Agent Memory Server)
pip install adk-redis[memory]

# Install with search tools support (RedisVL)
pip install adk-redis[search]

# Install all features
pip install adk-redis[all]
```

## Quick Start

### Two-Tier Memory Architecture (Recommended)

The recommended setup uses both `RedisWorkingMemorySessionService` and
`RedisLongTermMemoryService` together for complete memory capabilities:

```python
from google.adk import Agent
from google.adk.runners import Runner

from adk_redis.memory import RedisLongTermMemoryService, RedisLongTermMemoryServiceConfig
from adk_redis.sessions import (
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

# Configure session service (Tier 1: Working Memory)
session_config = RedisWorkingMemorySessionServiceConfig(
    api_base_url="http://localhost:8000",  # Agent Memory Server URL
    default_namespace="my_app",
    model_name="gpt-4o",  # Model for auto-summarization
    context_window_max=8000,  # Trigger summarization at this token count
)
session_service = RedisWorkingMemorySessionService(config=session_config)

# Configure memory service (Tier 2: Long-Term Memory)
memory_config = RedisLongTermMemoryServiceConfig(
    api_base_url="http://localhost:8000",
    default_namespace="my_app",
    extraction_strategy="discrete",  # Extract individual facts
    recency_boost=True,  # Prioritize recent memories in search
)
memory_service = RedisLongTermMemoryService(config=memory_config)

# Create agent
agent = Agent(
    name="memory_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant with long-term memory.",
)

# Create runner with both services
runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

**How it works:**

1. **Working Memory** stores session messages, state, and handles auto-summarization
2. **Background extraction** automatically promotes important information to long-term memory
3. **Long-Term Memory** provides semantic search across all sessions for relevant context

### Search Tools

```python
from google.adk import Agent
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis.tools import RedisVectorSearchTool, RedisVectorQueryConfig

# Create a vectorizer (HuggingFace, OpenAI, Cohere, etc.)
vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")

# Connect to existing search index
index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")

# Create the search tool
search_tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisVectorQueryConfig(
        vector_field_name="embedding",
        return_fields=["name", "description", "price"],
        num_results=5,
    ),
)

# Use with an ADK agent
agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    instruction="Help users find products using semantic search.",
    tools=[search_tool],
)
```

## Features

### Memory Services

| Service | Description |
|---------|-------------|
| `RedisLongTermMemoryService` | Implements ADK's `BaseMemoryService` for persistent long-term memory. Provides semantic search across all sessions with recency boosting, automatic memory extraction (facts, preferences, episodic), and cross-session knowledge retrieval. |

### Session Services

| Service | Description |
|---------|-------------|
| `RedisWorkingMemorySessionService` | Implements ADK's `BaseSessionService` for session management. Stores conversation messages and session state, provides automatic summarization when context limits are exceeded, and triggers background memory extraction to long-term storage. |

### Search Tools

| Tool | Description |
|------|-------------|
| `RedisVectorSearchTool` | Semantic similarity search using vector embeddings. Best for finding conceptually similar content. |
| `RedisHybridSearchTool` | Combines vector similarity with full-text search for improved recall. Supports both native Redis 8.4+ hybrid queries and aggregation-based fallback. |
| `RedisRangeSearchTool` | Range-based vector search with distance threshold. Returns all results within a similarity radius. |
| `RedisTextSearchTool` | Full-text search using Redis Search. Best for keyword-based queries without embeddings. |

## Requirements

- Python 3.10+
- For memory/session services: [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- For search tools: [Redis Stack](https://redis.io/docs/stack/) (Redis with Search module)
- Google ADK 1.0.0+

## Examples

See the [`examples/`](examples/) directory for complete working examples:

- **[redis_memory](examples/redis_memory/)**: Two-tier memory architecture with ADK web runner
- **[redis_search_tools](examples/redis_search_tools/)**: Vector, text, and range search tools

## Development

This project follows [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
conventions, matching the [ADK-Python core](https://github.com/google/adk-python) project.

```bash
# Clone the repository
git clone https://github.com/redis-applied-ai/adk-redis.git
cd adk-redis

# Install development dependencies
make dev

# Run all checks (format, lint, type-check, test)
make check

# Individual commands
make format      # Format code with pyink and isort
make lint        # Run ruff linter
make type-check  # Run mypy type checker
make test        # Run pytest test suite
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed coding style guidelines,
type hint conventions, and contribution process.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/redis-applied-ai/adk-redis)
- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- [RedisVL Documentation](https://docs.redisvl.com/)
- [Google ADK](https://github.com/google/adk-python)
