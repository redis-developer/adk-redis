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

"""Tavily Web Search Tool for ADK.

This tool provides web search capabilities using the Tavily API with Redis caching
to avoid rate limiting and reduce costs.

Environment variables:
- TAVILY_API_KEY: Required for Tavily API access
- REDIS_URL: Optional, defaults to redis://localhost:6379
"""

import json
import os
from typing import Any

from google.adk.tools import BaseTool
from google.genai import types

try:
  from redis import Redis
except ImportError:
  Redis = None  # type: ignore

try:
  import httpx
except ImportError:
  httpx = None  # type: ignore


class TavilySearchTool(BaseTool):
  """Web search tool using Tavily API with Redis caching.

  This tool searches the web for current information and caches results
  in Redis to avoid rate limiting and reduce API costs.

  Args:
      tavily_api_key: Tavily API key (or set TAVILY_API_KEY env var)
      redis_url: Redis connection URL (default: redis://localhost:6379)
      max_results: Maximum number of search results to return (default: 3)
      cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)
      name: Tool name (default: "web_search")
      description: Tool description
  """

  def __init__(
      self,
      *,
      tavily_api_key: str | None = None,
      redis_url: str | None = None,
      max_results: int = 3,
      cache_ttl: int = 3600,
      name: str = "web_search",
      description: str = (
          "Search the web for current information about travel destinations, "
          "requirements, weather, events, or any other travel-related queries. "
          "Use this when you need up-to-date information."
      ),
  ):
    super().__init__(name=name, description=description)

    # Get API key
    self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
    if not self.tavily_api_key:
      raise ValueError(
          "Tavily API key required. Set TAVILY_API_KEY environment variable "
          "or pass tavily_api_key parameter."
      )

    # Check dependencies
    if Redis is None:
      raise ImportError(
          "redis package required for TavilySearchTool. "
          "Install with: pip install redis"
      )
    if httpx is None:
      raise ImportError(
          "httpx package required for TavilySearchTool. "
          "Install with: pip install httpx"
      )

    # Setup Redis client for caching
    redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
      self.redis_client = Redis.from_url(redis_url, decode_responses=True)
      self.redis_client.ping()
      self.cache_enabled = True
    except Exception as e:
      print(f"Warning: Redis caching disabled - {e}")
      self.redis_client = None
      self.cache_enabled = False

    self.max_results = max_results
    self.cache_ttl = cache_ttl
    self.tavily_api_url = "https://api.tavily.com/search"

  def _get_declaration(self) -> types.FunctionDeclaration:
    """Return the tool declaration for ADK."""
    return types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING,
                    description="The search query to find relevant travel information",
                ),
            },
            required=["query"],
        ),
    )

  async def run_async(self, **kwargs: Any) -> dict[str, Any]:
    """Execute web search with caching.

    Args:
        **kwargs: Tool parameters (ADK passes in kwargs['args'])

    Returns:
        dict with search results
    """
    # ADK passes parameters in kwargs['args']
    args = kwargs.get("args", kwargs)
    query = args.get("query")

    if not query:
      return {
          "success": False,
          "error": "Search query is required",
      }

    # Check cache first
    if self.cache_enabled:
      cache_key = f"tavily_search:{query}"
      cached_result = self.redis_client.get(cache_key)  # type: ignore
      if cached_result:
        print(f"🔍 Web search (cached): {query}")
        return {
            "success": True,
            "results": json.loads(cached_result),
            "cached": True,
        }

    # Perform search via Tavily API
    print(f"🔍 Web search (live): {query}")
    try:
      async with httpx.AsyncClient() as client:
        response = await client.post(
            self.tavily_api_url,
            json={
                "api_key": self.tavily_api_key,
                "query": query,
                "max_results": self.max_results,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

      # Extract and format results
      results = []
      for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", "No title"),
                "content": item.get("content", "No content"),
                "url": item.get("url", ""),
            }
        )

      # Cache the results
      if self.cache_enabled and results:
        cache_key = f"tavily_search:{query}"
        self.redis_client.set(  # type: ignore
            cache_key,
            json.dumps(results),
            ex=self.cache_ttl,
        )

      return {
          "success": True,
          "results": results,
          "cached": False,
      }

    except httpx.HTTPError as e:
      return {
          "success": False,
          "error": f"HTTP error during web search: {str(e)}",
      }
    except Exception as e:
      return {
          "success": False,
          "error": f"Error performing web search: {str(e)}",
      }
