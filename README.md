# RedisVL ADK Integration

Redis Vector Library integration for Google Agent Development Kit (ADK) - providing memory, sessions, and semantic tools for AI agents.

[![CI](https://github.com/redis-applied-ai/redisvl-adk-agents/actions/workflows/ci.yml/badge.svg)](https://github.com/redis-applied-ai/redisvl-adk-agents/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

## Features

- **RedisVLMemoryService**: Semantic memory service using vector search
- **Vector Search Tool**: RAG-style document retrieval
- **Semantic Cache Tool**: LLM response caching with semantic similarity
- **Semantic Router Tool**: Intent-based routing for multi-agent systems
- **RedisVLSessionService** (Optional): Enhanced session service with semantic search

## Installation

```bash
pip install redisvl-adk
```

### With Optional Dependencies

```bash
# For OpenAI embeddings
pip install redisvl-adk[openai]

# For Cohere embeddings
pip install redisvl-adk[cohere]

# For HuggingFace embeddings
pip install redisvl-adk[huggingface]

# For development
pip install redisvl-adk[dev]
```

## Quick Start

### 1. RAG Chatbot with Memory

```python
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from redisvl_adk.memory import RedisVLMemoryService
from redisvl_adk.tools import create_vector_search_tool
from redisvl.utils.vectorize import OpenAITextVectorizer

# Initialize memory service
memory_service = RedisVLMemoryService(
    redis_url="redis://localhost:6379",
    vectorizer=OpenAITextVectorizer(api_key="your-api-key")
)

# Create vector search tool
vector_search = create_vector_search_tool(
    index=your_document_index,
    vectorizer=OpenAITextVectorizer(api_key="your-api-key")
)

# Create agent
agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    tools=[vector_search]
)

# Run with memory
runner = Runner(agent=agent, memory_service=memory_service)
response = await runner.run(
    app_name="my_app",
    user_id="user123",
    user_message="What are the benefits of Redis?"
)
```

### 2. Semantic Cache for Cost Optimization

```python
from redisvl.extensions.llmcache import SemanticCache
from redisvl_adk.tools import create_semantic_cache_tool

# Initialize cache
cache = SemanticCache(
    name="llm_cache",
    redis_url="redis://localhost:6379"
)

# Create cache tools
cache_tools = create_semantic_cache_tool(cache)

# Use in agent
agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    tools=cache_tools
)
```

### 3. Multi-Agent Routing

```python
from redisvl.extensions.router import SemanticRouter, Route
from redisvl_adk.tools import create_semantic_router_tool

# Define routes
routes = [
    Route(name="support", utterances=["help", "issue", "problem"]),
    Route(name="sales", utterances=["pricing", "demo", "purchase"])
]

# Create router
router = SemanticRouter(
    name="agent_router",
    routes=routes,
    redis_url="redis://localhost:6379"
)

# Create routing tool
router_tool = create_semantic_router_tool(router)
```

## Requirements

- Python 3.9+
- Redis Stack 7.2+ (for vector search)
- Google ADK
- RedisVL

## Documentation

- [Installation Guide](docs/installation.md)
- [Quick Start](docs/quickstart.md)
- [API Reference](docs/api/)
- [Examples](redisvl_adk/examples/)
- [Migration Guide](docs/migration_guide.md)

## Examples

See the [examples directory](redisvl_adk/examples/) for complete working examples:

- [RAG Chatbot](redisvl_adk/examples/rag_chatbot.py)
- [Semantic Cache Agent](redisvl_adk/examples/semantic_cache_agent.py)
- [Multi-Agent Router](redisvl_adk/examples/multi_agent_router.py)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- [RedisVL Documentation](https://docs.redisvl.com)
- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Redis Stack](https://redis.io/docs/stack/)
- [GitHub Repository](https://github.com/redis-applied-ai/redisvl-adk-agents)

## Support

- [GitHub Issues](https://github.com/redis-applied-ai/redisvl-adk-agents/issues)
- [Redis Discord](https://discord.gg/redis)
- [Redis Community](https://redis.io/community/)
