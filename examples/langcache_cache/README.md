# LangCache Semantic Cache Sample

This sample demonstrates how to use [Redis LangCache](https://redis.io/langcache)
with ADK agents for managed semantic caching. Unlike the local `SemanticCache`
example, LangCache handles embedding generation and vector storage server-side
-- no local vectorizer or Redis instance is required.

## Prerequisites

- Python 3.10+ (Python 3.12+ recommended)
- A LangCache account ([sign up](https://redis.io/langcache))
- ADK and adk-redis installed
- Google API key (for the LLM)

## Setup

### 1. Install Dependencies

First, install [uv](https://docs.astral.sh/uv/) if you haven't already:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

Then install the package with LangCache support:

```bash
uv pip install "adk-redis[langcache]" python-dotenv
```

### 2. Configure Environment Variables

Create a `.env` file in this directory:

```bash
# Required: Google API key for the agent
GOOGLE_API_KEY=your-google-api-key

# Required: LangCache credentials (from https://redis.io/langcache)
LANGCACHE_CACHE_ID=your-cache-id
LANGCACHE_API_KEY=your-api-key

# Optional: LangCache server URL (defaults to US East)
# LANGCACHE_SERVER_URL=https://aws-us-east-1.langcache.redis.io
```

## Usage

### Option 1: Run the Demo Script

```bash
uv run python main.py
```

This runs a demo that:
1. Creates an agent with LangCache semantic caching enabled
2. Sends multiple queries, including semantically similar ones
3. Shows cache hits for similar queries

### Option 2: Use with ADK Web

```bash
adk web .
```

Then open http://localhost:8000 to interact with the cached agent.

## Sample Structure

```
langcache_cache/
├── main.py                    # Demo script
├── langcache_agent/
│   ├── __init__.py            # Agent package initialization
│   └── agent.py               # Agent with LangCache caching callbacks
└── README.md                  # This file
```

## How It Works

1. **Before Model Callback**: Checks LangCache for a semantically similar
   prompt. If found, returns the cached response immediately.

2. **After Model Callback**: Stores the prompt-response pair in LangCache
   for future similar queries.

3. **Managed Embeddings**: LangCache generates embeddings server-side using
   optimized models. No local vectorizer setup is needed.

4. **Exact + Semantic Search**: By default, LangCache uses both exact hash
   matching and semantic vector search to maximize cache hit rates.

## Comparison with Local Semantic Cache

| Feature | Local (`semantic_cache`) | Managed (`langcache_cache`) |
|---------|--------------------------|----------------------------|
| Vectorizer | Local (HuggingFace, OpenAI, etc.) | Server-side (managed) |
| Redis instance | Required | Not required |
| Install extra | `adk-redis[search]` | `adk-redis[langcache]` |
| Provider class | `RedisVLCacheProvider` | `LangCacheProvider` |
| Setup complexity | Higher (Redis + vectorizer) | Lower (API key only) |

## Configuration Options

### LangCacheProviderConfig

- `cache_id` (str): LangCache cache ID (required)
- `api_key` (str): LangCache API key (required)
- `server_url` (str): LangCache server URL
- `name` (str): Cache name identifier
- `ttl` (int | None): Time-to-live in seconds for cached entries
- `distance_threshold` (float | None): Semantic similarity threshold
- `use_exact_search` (bool): Enable exact hash matching (default: True)
- `use_semantic_search` (bool): Enable semantic vector search (default: True)

### LLMResponseCacheConfig

- `first_message_only` (bool): Only cache first message in session
- `include_app_name` (bool): Include app name in cache key
- `include_user_id` (bool): Include user ID in cache key
- `include_session_id` (bool): Include session ID in cache key

## Learn More

- [LangCache Documentation](https://redis.io/langcache)
- [ADK Documentation](https://google.github.io/adk-docs)
- [RedisVL Documentation](https://redis.io/docs/latest/integrate/redisvl/)

