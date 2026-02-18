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

"""Travel Agent Hybrid: Full Session + Memory Services with Memory Tools.

This example demonstrates the HYBRID approach combining:
1. RedisWorkingMemorySessionService - For session management with auto-summarization
2. RedisLongTermMemoryService - For persistent long-term memory search
3. Memory Tools - For explicit LLM-controlled memory operations

This provides the complete two-tier memory architecture with both:
- Framework-managed memory (automatic extraction, summarization)
- LLM-controlled memory (explicit search, create, update, delete)
"""

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.cli.service_registry import get_service_registry
import uvicorn

from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig
from adk_redis.sessions import RedisWorkingMemorySessionService
from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig

load_dotenv()


def parse_base_url(uri: str) -> str:
    """Parse URI to extract base URL."""
    parsed = urlparse(uri)
    location = parsed.netloc + parsed.path
    return (
        location
        if location.startswith(("http://", "https://"))
        else f"http://{location}"
    )


def redis_session_factory(uri: str, **kwargs):
    """Factory function for creating RedisWorkingMemorySessionService from URI."""
    base_url = parse_base_url(uri)
    config = RedisWorkingMemorySessionServiceConfig(
        api_base_url=base_url,
        default_namespace=os.getenv("NAMESPACE", "travel_agent_memory_hybrid"),
        model_name=os.getenv("REDIS_MEMORY_MODEL_NAME", "gpt-4o"),
        context_window_max=int(
            os.getenv("REDIS_MEMORY_CONTEXT_WINDOW", "8000")
        ),
        extraction_strategy=os.getenv(
            "REDIS_MEMORY_EXTRACTION_STRATEGY", "discrete"
        ),
    )
    return RedisWorkingMemorySessionService(config=config)


def redis_memory_factory(uri: str, **kwargs):
    """Factory function for creating RedisLongTermMemoryService from URI."""
    base_url = parse_base_url(uri)
    config = RedisLongTermMemoryServiceConfig(
        api_base_url=base_url,
        default_namespace=os.getenv("NAMESPACE", "travel_agent_memory_hybrid"),
        extraction_strategy=os.getenv(
            "REDIS_MEMORY_EXTRACTION_STRATEGY", "discrete"
        ),
        recency_boost=os.getenv("REDIS_MEMORY_RECENCY_BOOST", "true").lower()
        == "true",
        semantic_weight=float(os.getenv("REDIS_MEMORY_SEMANTIC_WEIGHT", "0.7")),
        recency_weight=float(os.getenv("REDIS_MEMORY_RECENCY_WEIGHT", "0.3")),
    )
    return RedisLongTermMemoryService(config=config)


# Register service factories
registry = get_service_registry()
registry.register_session_service("redis-working-memory", redis_session_factory)
registry.register_memory_service("redis-long-term-memory", redis_memory_factory)

# Build URIs from environment
server_url = (
    os.getenv("MEMORY_SERVER_URL", "http://localhost:8088")
    .replace("http://", "")
    .replace("https://", "")
)
SESSION_SERVICE_URI = f"redis-working-memory://{server_url}"
MEMORY_SERVICE_URI = f"redis-long-term-memory://{server_url}"

# Create the FastAPI app with both services
app: FastAPI = get_fast_api_app(
    agents_dir=".",
    session_service_uri=SESSION_SERVICE_URI,
    memory_service_uri=MEMORY_SERVICE_URI,
    web=True,
)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    namespace = os.getenv("NAMESPACE", "travel_agent_memory_hybrid")
    server = os.getenv("MEMORY_SERVER_URL", "http://localhost:8088")
    extraction = os.getenv("REDIS_MEMORY_EXTRACTION_STRATEGY", "discrete")
    context_window = os.getenv("REDIS_MEMORY_CONTEXT_WINDOW", "8000")

    print(f"""
Travel Agent Hybrid (adk-redis)
===============================
ADK Server:          http://localhost:{port}
Memory Server:       {server}
Namespace:           {namespace}
Extraction Strategy: {extraction}
Context Window:      {context_window} tokens

Services (Framework-Managed):
  - Session:  RedisWorkingMemorySessionService (auto-summarization)
  - Memory:   RedisLongTermMemoryService (semantic search)

Tools (LLM-Controlled):
  - SearchMemoryTool, CreateMemoryTool, UpdateMemoryTool, DeleteMemoryTool
  - preload_memory, load_memory (ADK built-in)
  - TavilySearchTool, ItineraryPlannerTool, CalendarExportTool

Hybrid Architecture:
  - Framework handles session persistence and memory extraction automatically
  - LLM can explicitly search/create/update/delete memories via tools
  - Best of both worlds: automatic + explicit memory management
""")
    uvicorn.run(app, host="0.0.0.0", port=port)
