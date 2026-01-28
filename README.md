# ADK-Redis

Redis integrations for Google's Agent Development Kit (ADK).

[![PyPI version](https://badge.fury.io/py/adk-redis.svg)](https://badge.fury.io/py/adk-redis)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/redis-applied-ai/adk-redis/workflows/CI/badge.svg)](https://github.com/redis-applied-ai/adk-redis/actions)

## Overview

`adk-redis` provides Redis-based implementations of ADK services and tools:

- **Memory Services**: Long-term agent memory using Redis Agent Memory Server
- **Session Services**: Working memory session management
- **Search Tools**: Vector, hybrid, range, and text search tools using RedisVL

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

### Memory Service

```python
from adk_redis import RedisLongTermMemoryService, RedisLongTermMemoryServiceConfig
from google.adk import Agent

# Configure the memory service
config = RedisLongTermMemoryServiceConfig(
    redis_url="redis://localhost:6379",
    session_id="my-session",
)

# Create the memory service
memory_service = RedisLongTermMemoryService(config=config)

# Use with an ADK agent
agent = Agent(
    name="my_agent",
    model="gemini-2.0-flash",
    memory_service=memory_service,
)
```

### Session Service

```python
from adk_redis import RedisWorkingMemorySessionService, RedisWorkingMemorySessionServiceConfig

# Configure the session service
config = RedisWorkingMemorySessionServiceConfig(
    redis_url="redis://localhost:6379",
)

# Create the session service
session_service = RedisWorkingMemorySessionService(config=config)

# Use with ADK Runner
from google.adk import Runner

runner = Runner(
    agent=agent,
    session_service=session_service,
)
```

### Search Tools

```python
from adk_redis import RedisVectorSearchTool, RedisVectorQueryConfig
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

# Create a vectorizer
vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")

# Create a search index (assumes index already exists in Redis)
index = SearchIndex.from_existing("my_index", redis_url="redis://localhost:6379")

# Configure the search tool
config = RedisVectorQueryConfig(
    index=index,
    vector_field_name="embedding",
    return_fields=["title", "content"],
    num_results=5,
)

# Create the search tool
search_tool = RedisVectorSearchTool(
    config=config,
    vectorizer=vectorizer,
)

# Use with an ADK agent
agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    tools=[search_tool],
)
```

## Features

### Memory Services

| Service | Description |
|---------|-------------|
| `RedisLongTermMemoryService` | Long-term memory using Redis Agent Memory Server with automatic summarization |

### Session Services

| Service | Description |
|---------|-------------|
| `RedisWorkingMemorySessionService` | Session management using Redis Working Memory API |

### Search Tools

| Tool | Description |
|------|-------------|
| `RedisVectorSearchTool` | Vector similarity search |
| `RedisHybridSearchTool` | Combined vector + text search |
| `RedisRangeSearchTool` | Range-based vector search |
| `RedisTextSearchTool` | Full-text search |

## Requirements

- Python 3.10+
- Redis Stack (for search tools) or Redis Agent Memory Server (for memory/session services)
- Google ADK 1.0.0+

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
- [Redis Agent Memory Server](https://redis.io/docs/latest/develop/ai/agent-memory-server/)
- [RedisVL Documentation](https://docs.redisvl.com/)
- [Google ADK](https://github.com/google/adk-python)
