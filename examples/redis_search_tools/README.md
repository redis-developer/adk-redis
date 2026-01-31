# Redis Search Tools Agent

This sample demonstrates using Redis search tools to give an ADK agent
access to a Redis-based knowledge base with multiple search capabilities.

## What This Sample Shows

- Setting up a Redis vector index with a schema
- Using 3 Redis search tools in one agent:
  - **RedisVectorSearchTool**: Semantic similarity search (KNN)
  - **RedisTextSearchTool**: Full-text keyword search (BM25)
  - **RedisRangeSearchTool**: Distance threshold search
- Integrating RedisVL with an ADK agent

## Prerequisites

1. **Redis 8.4** running locally (or Redis Cloud with Search capability)
   ```bash
   # Using Docker
   docker run -d --name redis -p 6379:6379 redis:8.4-alpine
   ```

   > **Note**: Redis 8.4 includes the Redis Query Engine (evolved from RediSearch) with native support for vector search, full-text search, and JSON operations.

2. **No API keys needed for embeddings** - uses Redis' open-source
   `redis/langcache-embed-v2` model (768 dimensions)

## Setup

1. Install [uv](https://docs.astral.sh/uv/) if you haven't already:
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Or with pip
   pip install uv
   ```

2. Install dependencies:
   ```bash
   uv pip install "adk-redis[all]"
   ```

3. Download NLTK stopwords (required for keyword search):
   ```bash
   python -c "import nltk; nltk.download('stopwords')"
   ```

4. Set environment variables (or create a `.env` file):
   ```bash
   export REDIS_URL=redis://localhost:6379
   export GOOGLE_API_KEY=your-google-api-key  # For Gemini LLM
   ```

4. Load sample data into Redis:
   ```bash
   cd examples/redis_search_tools
   uv run python load_data.py
   ```

5. Run the agent:
   ```bash
   cd examples/redis_search_tools
   uv run adk web redis_search_tools_agent
   ```

## Files

| File | Description |
|------|-------------|
| `schema.yaml` | Redis index schema defining document structure |
| `load_data.py` | Script to populate Redis with sample documents |
| `redis_search_tools_agent/agent.py` | Agent definition with Redis search tools |

## Search Tools

### semantic_search (RedisVectorSearchTool)
**Best for:** Conceptual questions, natural language queries.

**How it works:** Converts query to vector embedding, finds K nearest neighbors.

**Example queries:**
- "What is Redis?" → finds docs about Redis even without exact match
- "How do I build a chatbot?" → finds docs about "intelligent assistants"

### keyword_search (RedisTextSearchTool)
**Best for:** Exact terms, acronyms, technical jargon, API names.

**How it works:** BM25 text scoring algorithm - matches exact tokens.

**Example queries:**
- "HNSW algorithm" → exact match on "HNSW" acronym
- "BM25 formula" → finds docs containing "BM25"

### range_search (RedisRangeSearchTool)
**Best for:** Exhaustive retrieval, comprehensive coverage.

**How it works:** Returns ALL documents within a distance threshold.

**Example queries:**
- "Tell me everything about RAG pipelines" → returns all RAG-related docs
- "All Redis data structures" → comprehensive list

## Example Queries

| Query | Expected Tool | Why |
|-------|---------------|-----|
| "What is Redis?" | semantic_search | Conceptual question |
| "HNSW algorithm details" | keyword_search | Technical acronym |
| "Tell me everything about RAG" | range_search | Exhaustive retrieval |
| "How do I build a chatbot?" | semantic_search | Natural language |
| "BM25 formula" | keyword_search | Exact term lookup |

## Customization

### Using a Different Vectorizer

```python
from redisvl.utils.vectorize import HuggingFaceTextVectorizer

vectorizer = HuggingFaceTextVectorizer(
    model="sentence-transformers/all-MiniLM-L6-v2"
)
```

Note: Update `dims` in `schema.yaml` to match your model's embedding dimensions.

### Adding Filters

```python
from redisvl.query.filter import Tag
from adk_redis.tools import RedisVectorSearchTool, RedisVectorQueryConfig

config = RedisVectorQueryConfig(num_results=5)
redis_search = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=config,
    return_fields=["title", "content", "url", "category"],
    filter_expression=Tag("category") == "redis",  # Only search Redis docs
)
```

### Connecting to Redis Cloud

```bash
export REDIS_URL=redis://default:password@your-redis-cloud-host:port
```
