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

"""Load sample articles for the redisvl_mcp_search demo.

The rvl mcp server is configured to expose BM25 fulltext search over
`content`, so the dataset is short prose suited to keyword matches.
"""

import os
from pathlib import Path

from redisvl.index import SearchIndex

SAMPLE_ARTICLES = [
    {
        "title": "Vector Similarity Search in Redis",
        "content": (
            "Redis supports approximate nearest neighbor search via FLAT and "
            "HNSW indexes. HNSW trades index size and build time for sub-linear "
            "query latency at high recall. Each algorithm has runtime parameters "
            "such as EF for HNSW that tune the accuracy-latency tradeoff."
        ),
        "topic": "vectors",
        "url": "https://redis.io/docs/vectors/",
    },
    {
        "title": "Hybrid Search with FT.HYBRID",
        "content": (
            "Hybrid search combines BM25 text scoring with vector similarity. "
            "Redis 8.4 introduced the FT.HYBRID command for server-side fusion "
            "using either LINEAR weighting or Reciprocal Rank Fusion (RRF). "
            "Older Redis versions can fall back to client-side aggregation."
        ),
        "topic": "search",
        "url": "https://redis.io/docs/hybrid/",
    },
    {
        "title": "Semantic Caching for LLMs",
        "content": (
            "A semantic cache stores prompt-response pairs keyed by the prompt "
            "embedding. On a cache lookup the new prompt is embedded and the "
            "nearest stored entry is returned when its distance is below the "
            "configured threshold. This skips the LLM call for repeated or "
            "near-duplicate requests."
        ),
        "topic": "caching",
        "url": "https://redis.io/langcache",
    },
    {
        "title": "Long-Term Memory for Agents",
        "content": (
            "Agent memory layers working memory and long-term memory. Working "
            "memory holds the active conversation; promoted facts move to "
            "long-term memory where recency-boosted semantic search retrieves "
            "them on demand. Background extraction keeps the layers in sync."
        ),
        "topic": "memory",
        "url": "https://github.com/redis/agent-memory-server",
    },
    {
        "title": "RedisVL MCP Server",
        "content": (
            "The RedisVL MCP server exposes a configured Redis index over the "
            "Model Context Protocol. Search and upsert tools are wired with "
            "schema-aware descriptions so agents see allowed filters and "
            "return fields. The server supports stdio, SSE, and "
            "streamable-http transports and ships a read-only flag."
        ),
        "topic": "mcp",
        "url": "https://docs.redisvl.com/en/stable/user_guide/how_to_guides/mcp.html",
    },
    {
        "title": "Index Schemas in RedisVL",
        "content": (
            "An IndexSchema declares the fields stored in a Redis search index. "
            "Fields include text, tag, numeric, geo, and vector types. The "
            "schema drives how documents are loaded, how filters are parsed, "
            "and which fields are projected by default."
        ),
        "topic": "schemas",
        "url": "https://docs.redisvl.com/en/stable/user_guide/schemas.html",
    },
]


def load_data() -> None:
  """Create the article index and load sample documents."""
  schema_path = Path(__file__).parent / "schema.yaml"
  redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

  print(f"Connecting to Redis at {redis_url}")
  index = SearchIndex.from_yaml(str(schema_path))
  index.connect(redis_url)

  print("Creating index (will overwrite if exists)...")
  index.create(overwrite=True, drop=True)

  print(f"Loading {len(SAMPLE_ARTICLES)} articles...")
  keys = [f"{index.prefix}:{i:04d}" for i in range(len(SAMPLE_ARTICLES))]
  index.load(SAMPLE_ARTICLES, keys=keys)

  print(
      """
Loaded articles. Next:

  1. Start the rvl mcp server in another terminal:
       rvl mcp --config mcp_config.yaml \\
         --transport streamable-http --host 127.0.0.1 --port 8765
  2. Run the agent:
       adk web redisvl_mcp_search_agent
"""
  )


if __name__ == "__main__":
  load_data()
