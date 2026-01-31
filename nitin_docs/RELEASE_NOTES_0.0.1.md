# Release Notes: adk-redis v0.0.1 (Experimental)

**Release Date:** 2026-01-31  
**Status:** 🧪 Experimental Release

---

## Overview

First experimental release of **adk-redis**, providing Redis integrations for Google's Agent Development Kit (ADK). This release implements ADK's core interfaces using Redis Agent Memory Server and RedisVL.

> **⚠️ Experimental Notice**: This is an early experimental release. APIs may change in future versions. Not recommended for production use.

---

## What's Included

### 🧠 Memory Services

**Long-Term Memory** (`LongTermMemoryService`)
- Implements ADK's `BaseMemoryService` interface
- Semantic search across agent memories with recency boosting
- Automatic memory extraction from conversations
- Support for facts, preferences, and episodic memories
- Cross-session knowledge retrieval
- Integration with Redis Agent Memory Server

**Working Memory** (`WorkingMemoryService`)
- Implements ADK's `BaseSessionService` interface
- Session state management and persistence
- Automatic conversation summarization
- Context window management
- Background memory promotion to long-term storage

### 🔍 Search Tools

**Vector Search Tools** (via RedisVL)
- `VectorSearchTool` - Similarity search with optional filters
- `HybridSearchTool` - Combined vector + full-text search
- `RangeSearchTool` - Numeric/geo range queries
- `TextSearchTool` - Full-text search capabilities
- Support for multiple vectorizer backends (OpenAI, Cohere, HuggingFace, local models)

### 💬 Semantic Caching

**LLM Response Caching**
- `SemanticLLMCache` - Cache LLM responses with semantic similarity matching
- `SemanticToolCache` - Cache tool execution results
- Reduces latency and API costs
- Vector-based cache lookup
- Support for local embeddings (no API key required)

---

## Examples

Four complete working examples included:

1. **simple_redis_memory** - Two-tier memory architecture with auto-summarization
2. **semantic_cache** - LLM response caching with local embeddings
3. **redis_search_tools** - RAG implementation with search tools
4. **travel_agent_memory** - Full-featured travel agent with memory, web search, and multi-user support

Each example includes:
- Complete runnable code
- ADK web runner integration
- Docker Compose setup
- Detailed documentation

---

## Infrastructure & Tooling

### Automated Setup
- `scripts/setup-agent-memory-server.sh` - One-command setup for Agent Memory Server from source
- Automated prerequisite checking
- Build verification
- Clear next-step instructions

### Documentation
- Comprehensive README with quick start guide
- `docs/redis-setup.md` - Redis 8.4 setup and configuration
- `docs/agent-memory-server-setup.md` - Agent Memory Server setup guide
- `docs/integration-guide.md` - Integration patterns and best practices

### Development Tools
- Full type checking with mypy
- Code formatting with pyink (Google style)
- Import sorting with isort
- Linting with ruff
- GitHub Actions CI/CD pipeline
- Comprehensive test suite

---

## Key Features

✅ **Redis 8.4 Support** - Native Redis Query Engine with vector search, full-text search, and JSON operations  
✅ **LiteLLM Integration** - Support for 100+ LLM providers (OpenAI, Gemini, Anthropic, AWS Bedrock, Ollama, etc.)  
✅ **Local Embeddings** - No API key required for semantic caching (uses `redis/langcache-embed-v1`)  
✅ **Multi-User Support** - Namespace isolation for multi-tenant applications  
✅ **Flexible Deployment** - Works with local Redis, Redis Cloud, or containerized setups  
✅ **Type Safety** - Full type hints and mypy strict mode compliance  

---

## Requirements

- Python 3.10+
- Redis 8.4+ or Redis Cloud
- Redis Agent Memory Server (for memory/session services)
- Google ADK (`google-adk`)

---

## Installation

```bash
# Base package
pip install adk-redis

# With memory services
pip install adk-redis[memory]

# With search tools
pip install adk-redis[search]

# All features
pip install adk-redis[all]
```

---

## Known Issues & Limitations

1. **Agent Memory Server Build Required**: A recent bug fix for non-OpenAI provider support requires building Agent Memory Server from source (commit `b53557d` or later). Use the provided setup script: `./scripts/setup-agent-memory-server.sh`

2. **Experimental APIs**: All APIs are subject to change in future releases

3. **Limited Testing**: While core functionality is tested, edge cases may not be fully covered

4. **Documentation**: Some advanced features may lack detailed documentation

---

## What's Next

Planned for future releases:
- Stable API freeze (v0.1.0)
- Additional search tool types
- Performance optimizations
- Enhanced error handling
- More comprehensive documentation
- Additional examples

---

## Credits

**Developed by:** Redis Applied AI Team  
**License:** Apache 2.0  
**Repository:** https://github.com/redis-applied-ai/adk-redis

**Built with:**
- [Google Agent Development Kit (ADK)](https://github.com/google/adk-python)
- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- [RedisVL](https://docs.redisvl.com)
- [Redis 8.4](https://redis.io)

---

## Feedback

This is an experimental release and we welcome your feedback! Please report issues, suggestions, or questions:
- GitHub Issues: https://github.com/redis-applied-ai/adk-redis/issues
- Email: applied.ai@redis.com

