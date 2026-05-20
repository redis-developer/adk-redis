# Copyright 2025 Redis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Load the same knowledge base as redis_search_tools, but for MCP search.

The corpus mirrors `examples/redis_search_tools/load_data.py` so the
in-process and MCP demos answer the same questions on the same data.
Documents are embedded with `redis/langcache-embed-v2` (768 dims) so the
configured `rvl mcp` server can run vector or hybrid search against
them.
"""

import os
from pathlib import Path

from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer

SAMPLE_DOCS = [
    # === SEMANTIC SEARCH DEMOS ===
    {
        "title": "Introduction to Redis",
        "content": (
            "Redis is a lightning-fast in-memory data store. It excels at"
            " caching, session management, and real-time analytics. Think of"
            " it as a Swiss Army knife for data: versatile, quick, and"
            " reliable."
        ),
        "url": "https://redis.io/docs/about/",
        "category": "redis",
        "doc_type": "reference",
        "difficulty": "beginner",
    },
    {
        "title": "Understanding Vector Databases",
        "content": (
            "Vector databases store numerical representations of data called"
            " embeddings. These embeddings capture semantic meaning, enabling"
            " similarity search. Applications include recommendation engines,"
            " image search, and chatbots."
        ),
        "url": "https://redis.io/docs/vectors/",
        "category": "concepts",
        "doc_type": "reference",
        "difficulty": "intermediate",
    },
    {
        "title": "Building Intelligent Assistants",
        "content": (
            "Modern AI assistants combine language models with external"
            " knowledge. They can search databases, call APIs, and maintain"
            " conversation context. The key is giving them the right tools"
            " for each task."
        ),
        "url": "https://google.github.io/adk-docs/agents/",
        "category": "adk",
        "doc_type": "tutorial",
        "difficulty": "intermediate",
    },
    # === KEYWORD-FRIENDLY DEMOS ===
    {
        "title": "HNSW Algorithm Deep Dive",
        "content": (
            "HNSW (Hierarchical Navigable Small World) is the algorithm Redis"
            " uses for approximate nearest neighbor search. It builds a"
            " multi-layer graph where each layer has exponentially fewer"
            " nodes. Search starts at the top layer and navigates down."
            " Parameters: M (connections per node), EF (search width)."
        ),
        "url": "https://redis.io/docs/hnsw/",
        "category": "redis",
        "doc_type": "reference",
        "difficulty": "advanced",
    },
    {
        "title": "BM25 Scoring Explained",
        "content": (
            "BM25 (Best Matching 25) is a ranking function for full-text"
            " search. It improves on TF-IDF by adding document length"
            " normalization and term frequency saturation. Redis supports"
            " BM25STD and BM25 scorers."
        ),
        "url": "https://redis.io/docs/bm25/",
        "category": "redis",
        "doc_type": "reference",
        "difficulty": "advanced",
    },
    {
        "title": "Hybrid Search with FT.HYBRID",
        "content": (
            "Hybrid search combines BM25 text scoring with vector similarity."
            " Redis 8.4 introduced the FT.HYBRID command for server-side"
            " fusion using either LINEAR weighting or Reciprocal Rank Fusion"
            " (RRF). Older Redis versions fall back to client-side"
            " aggregation."
        ),
        "url": "https://redis.io/docs/hybrid/",
        "category": "redis",
        "doc_type": "reference",
        "difficulty": "advanced",
    },
    # === RAG-FOCUSED ===
    {
        "title": "RAG Architecture Overview",
        "content": (
            "Retrieval-Augmented Generation (RAG) enhances LLMs with external"
            " knowledge. Step 1: embed the user query. Step 2: search the"
            " vector database for relevant documents. Step 3: include"
            " retrieved context in the LLM prompt. Step 4: generate a"
            " grounded response."
        ),
        "url": "https://redis.io/solutions/rag/",
        "category": "concepts",
        "doc_type": "tutorial",
        "difficulty": "intermediate",
    },
    {
        "title": "RAG Best Practices",
        "content": (
            "Tips for effective RAG: chunk documents appropriately (512 to"
            " 1024 tokens), use hybrid search for better recall, rerank"
            " results before prompting, include metadata for filtering, and"
            " monitor retrieval quality metrics."
        ),
        "url": "https://redis.io/solutions/rag/best-practices/",
        "category": "concepts",
        "doc_type": "tutorial",
        "difficulty": "intermediate",
    },
    # === MCP-FOCUSED ===
    {
        "title": "RedisVL MCP Server",
        "content": (
            "The RedisVL MCP server exposes a configured Redis index over the"
            " Model Context Protocol. Search and upsert tools are wired with"
            " schema-aware descriptions so agents see allowed filters and"
            " return fields. The server supports stdio, SSE, and"
            " streamable-http transports and ships a read-only flag."
        ),
        "url": (
            "https://docs.redisvl.com/en/stable/user_guide/how_to_guides/mcp.html"
        ),
        "category": "redis",
        "doc_type": "reference",
        "difficulty": "intermediate",
    },
    # === FAQ STYLE ===
    {
        "title": "FAQ: Embedding Dimensions Mismatch",
        "content": (
            "Q: Dimension mismatch error? A: Ensure query embeddings match"
            " index dimensions. Common dimensions: OpenAI ada-002 (1536),"
            " langcache-embed-v2 (768), sentence-transformers (384 to 768)."
            " Check the schema dims field."
        ),
        "url": "https://redis.io/docs/faq/vectors/",
        "category": "redis",
        "doc_type": "faq",
        "difficulty": "beginner",
    },
]


def load_data() -> None:
  """Build the index and load documents with embeddings."""
  schema_path = Path(__file__).parent / "schema.yaml"
  redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

  print(f"Connecting to Redis at {redis_url}")
  index = SearchIndex.from_yaml(str(schema_path))
  index.connect(redis_url)

  print("Creating index (will overwrite if exists)...")
  index.create(overwrite=True, drop=True)

  print("Generating embeddings (redis/langcache-embed-v2)...")
  vectorizer = HFTextVectorizer(model="redis/langcache-embed-v2")

  docs_with_embeddings = []
  for doc in SAMPLE_DOCS:
    embedding = vectorizer.embed(doc["content"], as_buffer=True)
    docs_with_embeddings.append({**doc, "embedding": embedding})
    print(f"  [{doc['doc_type']:9}] {doc['title']}")

  print(f"\nLoading {len(SAMPLE_DOCS)} docs into Redis...")
  # Stable keys so re-running the loader overwrites instead of duplicating.
  keys = [f"{index.prefix}:{i:04d}" for i in range(len(SAMPLE_DOCS))]
  index.load(docs_with_embeddings, keys=keys)

  print(
      """
Loaded knowledge base. Next:

  1. Start the rvl mcp server in another terminal:
       rvl mcp --config mcp_config.yaml \\
         --transport streamable-http --host 127.0.0.1 --port 8765
  2. Run the agent:
       adk web redisvl_mcp_search_agent

Try prompts like the in-process redis_search_tools demo:
  - "What is Redis?"           (semantic)
  - "Tell me about HNSW"       (keyword)
  - "How does RAG work?"       (semantic)
  - "FT.HYBRID command"        (mixed semantic + keyword)
"""
  )


if __name__ == "__main__":
  load_data()
