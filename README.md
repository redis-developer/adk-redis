<div align="center">
  <h1>
    <img src="https://raw.githubusercontent.com/redis/redis-vl-python/main/docs/_static/Redis_Logo_Red_RGB.svg" width="120" alt="Redis" style="vertical-align: middle; margin-right: 20px;">
    <span style="vertical-align: middle; margin: 0 10px;">×</span>
    <img src="https://raw.githubusercontent.com/google/adk-python/main/assets/agent-development-kit.png" width="120" alt="ADK" style="vertical-align: middle; margin-left: 20px;">
  </h1>
  <h1>Redis Integrations for Google Agent Development Kit</h1>
</div>

<div align="center">

[![PyPI version](https://badge.fury.io/py/adk-redis.svg)](https://badge.fury.io/py/adk-redis)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: pyink](https://img.shields.io/badge/code%20style-pyink-black)](https://github.com/google/pyink)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)

**[PyPI](https://pypi.org/project/adk-redis/)** • **[Documentation](https://github.com/redis-developer/adk-redis)** • **[Examples](examples/)** • **[Agent Memory Server](https://github.com/redis/agent-memory-server)** • **[RedisVL](https://docs.redisvl.com)**

</div>

---

## Introduction

**adk-redis** provides Redis integrations for Google's Agent Development Kit (ADK). Implements ADK's `BaseMemoryService`, `BaseSessionService`, tool interfaces, and semantic caching using Redis Agent Memory Server and RedisVL.

<div align="center">

| 🔌 [**ADK Services**](#memory-services) | 🔧 [**Agent Tools**](#search-tools) | ⚡ [**Semantic Caching**](#semantic-caching) |
|:---:|:---:|:---:|
| **Memory Service**<br/>*Long-term memory via Agent Memory Server* | **Memory Tools**<br/>*LLM-controlled memory operations* | **LLM Response Cache**<br/>*Reduce latency & costs* |
| Semantic search & auto-extraction | search, create, update, delete | Similarity-based cache lookup |
| Cross-session knowledge retrieval | Direct Agent Memory Server API | Configurable distance threshold |
| Recency-boosted search | Namespace & user isolation | TTL-based expiration |
| **Session Service**<br/>*Working memory via Agent Memory Server* | **Search Tools**<br/>*RAG via RedisVL* | **Tool Cache**<br/>*Avoid redundant calls* |
| Context window management | Vector, hybrid, text, range search | Cache tool execution results |
| Auto-summarization | Multiple vectorizers supported | Reduce API calls |
| Background memory promotion | Metadata filtering | Configurable thresholds |

</div>



---

## Installation

### Install from PyPI

```bash
pip install adk-redis
```

### Optional Dependencies

Install with optional features based on your use case:

```bash
# Memory & session services (Redis Agent Memory Server integration)
pip install adk-redis[memory]

# Search tools (RedisVL integration)
pip install adk-redis[search]

# All features
pip install adk-redis[all]
```

### Verify Installation

```bash
python -c "from adk_redis import __version__; print(__version__)"
```

### Development Installation

For contributors or those who want the latest unreleased changes:

```bash
# Clone the repository
git clone https://github.com/redis-developer/adk-redis.git
cd adk-redis

# Install with uv (recommended for development)
pip install uv
uv sync --all-extras

# Or install directly from GitHub
pip install git+https://github.com/redis-developer/adk-redis.git@main
```

---

## Getting Started

### Prerequisites

**For memory/session services:**
- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server) (port 8088)
- Redis 8.4+ or Redis Cloud (backend for Agent Memory Server)

**For search tools:**
- Redis 8.4+ or Redis Cloud with Search capability

**Quick start:**

#### 1. Start Redis 8.4

Redis is required for all examples in this repository. Choose one of the following options:

**Option A: Automated setup (recommended)**

```bash
# Run from the repository root
./scripts/start-redis.sh
```

This script will:
- Check if Docker is installed and running
- Check if Redis is already running on port 6379
- Start Redis 8.4 in a Docker container with health checks
- Verify the Redis container is healthy and accepting connections
- Provide helpful commands for managing Redis

**Option B: Manual setup**

```bash
docker run -d --name redis -p 6379:6379 redis:8.4-alpine
```

> **Note**: Redis 8.4 includes the Redis Query Engine (evolved from RediSearch) with native support for vector search, full-text search, and JSON operations. Docker will automatically download the image (~40MB) on first run.

**Verify Redis is running:**

```bash
# Check container status
docker ps | grep redis

# Test connection
docker exec redis redis-cli ping
# Should return: PONG

# Or if you have redis-cli installed locally
redis-cli -p 6379 ping
```

**Common Redis commands:**

```bash
# View logs
docker logs redis
docker logs -f redis  # Follow logs in real-time

# Stop Redis
docker stop redis

# Restart Redis
docker restart redis

# Remove Redis (stops and deletes container)
docker rm -f redis
```

**Troubleshooting:**

- **Port 6379 already in use**: Another process is using the port. Find it with `lsof -i :6379` or use a different port: `docker run -d --name redis -p 6380:6379 redis:8.4-alpine`
- **Docker not running**: Start Docker Desktop or the Docker daemon
- **Permission denied**: Run with `sudo` or add your user to the docker group
- **Container won't start**: Check logs with `docker logs redis`

#### 2. Start Agent Memory Server

```bash
docker run -d --name agent-memory-server -p 8088:8088 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e FAST_MODEL=gemini/gemini-2.0-flash \
  -e SLOW_MODEL=gemini/gemini-2.0-flash \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
```

> **Configuration Options:**
> - **LLM Provider**: Agent Memory Server uses [LiteLLM](https://docs.litellm.ai/) and supports 100+ providers (OpenAI, Gemini, Anthropic, AWS Bedrock, Ollama, etc.). Set the appropriate environment variables for your provider (e.g., `GEMINI_API_KEY`, `GENERATION_MODEL=gemini/gemini-2.0-flash`). See the [Agent Memory Server LLM Providers docs](https://redis.github.io/agent-memory-server/llm-providers/) for details.
> - **Model Configuration**: Set `GENERATION_MODEL`, `FAST_MODEL` (for quick tasks like extraction), and `SLOW_MODEL` (for complex tasks) to your preferred models. All default to OpenAI models if not specified.
> - **Memory Extraction Debounce**: `EXTRACTION_DEBOUNCE_SECONDS` controls how long to wait before extracting memories from a conversation (default: 300 seconds). Lower values (e.g., 5) provide faster memory extraction, while higher values reduce API calls.
> - **Embedding Models**: Agent Memory Server also uses LiteLLM for embeddings. For local/offline embeddings, use Ollama (e.g., `EMBEDDING_MODEL=ollama/nomic-embed-text`, `REDISVL_VECTOR_DIMENSIONS=768`). See [Embedding Providers docs](https://redis.github.io/agent-memory-server/embedding-providers/) for all options.

**See detailed setup guides:**
- [Redis Setup Guide](docs/redis-setup.md) - All Redis deployment options
- [Agent Memory Server Setup](docs/agent-memory-server-setup.md) - Complete configuration
- [Integration Guide](docs/integration-guide.md) - End-to-end setup with code examples

---

## Quick Start

### Two-Tier Memory Architecture

Uses both working memory (session-scoped) and long-term memory (persistent):

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
    api_base_url="http://localhost:8088",  # Agent Memory Server URL
    default_namespace="my_app",
    model_name="gpt-4o",  # Model for auto-summarization
    context_window_max=8000,  # Trigger summarization at this token count
)
session_service = RedisWorkingMemorySessionService(config=session_config)

# Configure memory service (Tier 2: Long-Term Memory)
memory_config = RedisLongTermMemoryServiceConfig(
    api_base_url="http://localhost:8088",
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

1. **Working Memory**: Stores session messages, state, and handles auto-summarization
2. **Background Extraction**: Automatically promotes important information to long-term memory
3. **Long-Term Memory**: Provides semantic search across all sessions for relevant context
4. **Recency Boosting**: Prioritizes recent memories while maintaining access to historical knowledge

### Vector Search Tools

RAG with semantic search using RedisVL:

```python
from google.adk import Agent
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

from adk_redis.tools import RedisVectorSearchTool, RedisVectorQueryConfig

# Create a vectorizer (HuggingFace, OpenAI, Cohere, Mistral, Voyage AI, etc.)
vectorizer = HFTextVectorizer(model="sentence-transformers/all-MiniLM-L6-v2")

# Connect to existing search index
index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")

# Create the search tool with custom name and description
search_tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisVectorQueryConfig(
        vector_field_name="embedding",
        return_fields=["name", "description", "price"],
        num_results=5,
    ),
    # Customize the tool name and description for your domain
    name="search_product_catalog",
    description="Search to find relevant products in the product catalog by description semantic similarity",
)

# Use with an ADK agent
agent = Agent(
    name="search_agent",
    model="gemini-2.0-flash",
    instruction="Help users find products using semantic search.",
    tools=[search_tool],
)
```

**Customizing Tool Prompts:**

All search tools (`RedisVectorSearchTool`, `RedisHybridSearchTool`, `RedisTextSearchTool`, `RedisRangeSearchTool`) support custom `name` and `description` parameters to make them domain-specific:

```python
# Example: Medical knowledge base
medical_search = RedisVectorSearchTool(
    index=medical_index,
    vectorizer=vectorizer,
    name="search_medical_knowledge",
    description="Search medical literature and clinical guidelines for relevant information",
)

# Example: Customer support FAQ
faq_search = RedisTextSearchTool(
    index=faq_index,
    name="search_support_articles",
    description="Search customer support articles and FAQs by keywords",
)

# Example: Legal document search
legal_search = RedisHybridSearchTool(
    index=legal_index,
    vectorizer=vectorizer,
    name="search_legal_documents",
    description="Search legal documents using both semantic similarity and keyword matching",
)
```

> **Note:** RedisVL supports many vectorizers including OpenAI, HuggingFace, Cohere, Mistral, Voyage AI, and more. See [RedisVL documentation](https://docs.redisvl.com/) for the full list.

> **Future Enhancement:** We plan to add native support for ADK embeddings classes through a union type or wrapper, allowing seamless integration with ADK's embedding infrastructure alongside RedisVL vectorizers.

---

## Features Overview

### Memory Services

Implements ADK's `BaseMemoryService` interface for persistent agent memory:

| Feature | Description |
|---------|-------------|
| **Semantic Search** | Vector-based similarity search across all sessions |
| **Recency Boosting** | Prioritize recent memories while maintaining historical access |
| **Auto-Extraction** | LLM-based extraction of facts, preferences, and episodic memories |
| **Cross-Session Retrieval** | Access knowledge from any previous conversation |
| **Background Processing** | Non-blocking memory promotion and indexing |

**Implementation:** `RedisLongTermMemoryService`

### Session Services

Implements ADK's `BaseSessionService` interface for conversation management:

| Feature | Description |
|---------|-------------|
| **Message Storage** | Persist conversation messages and session state |
| **Auto-Summarization** | Automatic summarization when context window limits are exceeded |
| **Memory Promotion** | Trigger background extraction to long-term memory |
| **State Management** | Store and retrieve arbitrary session state |
| **Token Tracking** | Monitor context window usage |

**Implementation:** `RedisWorkingMemorySessionService`

### Search Tools

Four specialized search tools for different RAG use cases:

| Tool | Best For | Key Features |
|------|----------|--------------|
| **`RedisVectorSearchTool`** | Semantic similarity | Vector embeddings, KNN search, metadata filtering |
| **`RedisHybridSearchTool`** | Combined search | Vector + text search, Redis 8.4+ native support, aggregation fallback |
| **`RedisRangeSearchTool`** | Threshold-based retrieval | Distance-based filtering, similarity radius |
| **`RedisTextSearchTool`** | Keyword search | Full-text search, no embeddings required |

> All search tools support multiple vectorizers (OpenAI, HuggingFace, Cohere, Mistral, Voyage AI, etc.) and advanced filtering.

### Semantic Caching

Reduce latency and costs with similarity-based caching:

| Feature | Description |
|---------|-------------|
| **LLM Response Cache** | Cache LLM responses and return similar cached results |
| **Tool Result Cache** | Cache tool execution results to avoid redundant calls |
| **Similarity Threshold** | Configurable distance threshold for cache hits |
| **TTL Support** | Time-based cache expiration |
| **Multiple Vectorizers** | Support for OpenAI, HuggingFace, local embeddings, etc. |

**Implementations:** `LLMResponseCache`, `ToolCache`

---

## Requirements

- **Python** 3.10, 3.11, 3.12, or 3.13
- **Google ADK** 1.0.0+
- **For memory/session services:** [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- **For search tools:** Redis 8.4+ or Redis Cloud with Search capability

---

## Examples

Complete working examples with ADK web runner integration:

| Example | Description | Features |
|---------|-------------|----------|
| **[simple_redis_memory](examples/simple_redis_memory/)** | Agent with two-tier memory architecture | Working memory, long-term memory, auto-summarization, semantic search |
| **[semantic_cache](examples/semantic_cache/)** | Semantic caching for LLM responses | Vector-based cache, reduced latency, cost optimization, local embeddings |
| **[redis_search_tools](examples/redis_search_tools/)** | RAG with search tools | Vector search, hybrid search, range search, text search |
| **[travel_agent_memory_hybrid](examples/travel_agent_memory_hybrid/)** | Travel agent with framework-managed memory | Redis session + memory services, automatic memory extraction, web search, calendar export, itinerary planning |
| **[travel_agent_memory_tools](examples/travel_agent_memory_tools/)** | Travel agent with LLM-controlled memory | Memory tools only (search/create/update/delete), in-memory session, web search, calendar export, itinerary planning |

### Travel Agent Examples Comparison

Both examples use **Redis Agent Memory Server** for long-term memory persistence. The difference is in how they integrate with ADK:

| Aspect | `travel_agent_memory_hybrid` | `travel_agent_memory_tools` |
|--------|------------------------------|----------------------------|
| **How to Run** | `python main.py` (custom FastAPI) | `adk web .` (standard ADK CLI) |
| **Session Service** | `RedisWorkingMemorySessionService` (Redis-backed, auto-summarization) | ADK default (in-memory) |
| **Memory Service** | `RedisLongTermMemoryService` (ADK's `BaseMemoryService` interface) | Memory tools only (direct Agent Memory Server API calls) |
| **Memory Extraction** | `after_agent_callback` + framework-managed | `after_agent_callback` |
| **Session Sync** | Real-time (every message synced to Agent Memory Server) | End-of-turn (batch sync via `after_agent_callback`) |
| **Auto-Summarization** | Yes, mid-conversation (real-time sync triggers when context exceeded) | Yes, end-of-turn (batch sync triggers when context exceeded) |
| **Best For** | Full ADK service integration (`BaseSessionService` + `BaseMemoryService`) | Tool-based Agent Memory Server integration (no custom services) |

Each example includes:
- Complete runnable code
- ADK web runner integration
- Configuration examples
- Setup instructions

---

## Development

This project follows the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), matching the [ADK-Python core](https://github.com/google/adk-python) project conventions.

### Quick Start

```bash
# Clone the repository
git clone https://github.com/redis-developer/adk-redis.git
cd adk-redis

# Install development dependencies
make dev

# Run all checks (format, lint, type-check, test)
make check
```

### Available Commands

```bash
make format      # Format code with pyink and isort
make lint        # Run ruff linter
make type-check  # Run mypy type checker
make test        # Run pytest test suite
make coverage    # Generate coverage report
```

### Code Quality
See **[CONTRIBUTING.md](CONTRIBUTING.md)** for coding style, type hints, testing, and PR guidelines.

---

## Contributing

Please help us by contributing PRs, opening GitHub issues for bugs or new feature ideas, improving documentation, or increasing test coverage. See the following steps for contributing:

1. [Open an issue](https://github.com/redis-developer/adk-redis/issues) for bugs or feature requests
2. Read [CONTRIBUTING.md](CONTRIBUTING.md) and submit a pull request
3. Improve documentation and examples

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

## Helpful Links

### Documentation & Resources
- **[PyPI Package](https://pypi.org/project/adk-redis/)** - Install with `pip install adk-redis`
- **[GitHub Repository](https://github.com/redis-developer/adk-redis)** - Source code and issue tracking
- **[Examples](examples/)** - Complete working examples with ADK web runner
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to the project

### Setup Guides
- **[Redis Setup Guide](docs/redis-setup.md)** - All Redis deployment options
- **[Agent Memory Server Setup](docs/agent-memory-server-setup.md)** - Complete configuration
- **[Integration Guide](docs/integration-guide.md)** - End-to-end setup with code examples

### Related Projects
- **[Google ADK](https://github.com/google/adk-python)** - Agent Development Kit framework
- **[Redis Agent Memory Server](https://github.com/redis/agent-memory-server)** - Memory layer for AI agents
- **[RedisVL](https://docs.redisvl.com/)** - Redis Vector Library documentation
- **[Redis](https://redis.io/)** - Redis 8.4+ with Search, JSON, and vector capabilities

---
