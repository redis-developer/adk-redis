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

"""Example of using LangCache (managed semantic cache) with ADK agents.

LangCache is a managed semantic caching service by Redis that handles
embedding generation and vector storage server-side. No local vectorizer
or Redis instance is required.

Set the following environment variables before running:
  LANGCACHE_CACHE_ID  - Your LangCache cache ID
  LANGCACHE_API_KEY   - Your LangCache API key
  GOOGLE_API_KEY      - Google API key for the LLM
"""

import asyncio
import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from adk_redis.cache import create_llm_cache_callbacks
from adk_redis.cache import LangCacheCacheProvider
from adk_redis.cache import LangCacheCacheProviderConfig
from adk_redis.cache import LLMResponseCache
from adk_redis.cache import LLMResponseCacheConfig

# Load environment variables
load_dotenv()


def create_cached_agent() -> tuple[Agent, LLMResponseCache]:
  """Create an agent with LangCache semantic caching enabled."""
  # Create LangCache provider (managed -- no local vectorizer needed)
  provider = LangCacheCacheProvider(
      config=LangCacheCacheProviderConfig(
          cache_id=os.environ["LANGCACHE_CACHE_ID"],
          api_key=os.environ["LANGCACHE_API_KEY"],
          server_url=os.getenv(
              "LANGCACHE_SERVER_URL",
              "https://aws-us-east-1.langcache.redis.io",
          ),
          ttl=3600,  # 1 hour TTL
      ),
  )

  # Create LLM response cache
  llm_cache = LLMResponseCache(
      provider=provider,
      config=LLMResponseCacheConfig(
          first_message_only=True,  # Only cache first message in session
          include_app_name=True,
          include_user_id=True,
      ),
  )

  # Create callback functions
  before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

  # Create agent with caching callbacks
  agent = Agent(
      name="langcache_assistant",
      model="gemini-2.0-flash",
      instruction="""You are a helpful assistant. Answer questions clearly
      and concisely. When asked about programming, provide practical examples.""",
      before_model_callback=before_cb,
      after_model_callback=after_cb,
  )

  return agent, llm_cache


async def main():
  """Run the LangCache cached agent demo."""
  print("""Creating LangCache cached agent...
No local vectorizer or Redis instance needed -- LangCache handles it all.""")
  agent, llm_cache = create_cached_agent()

  # Create session service and runner
  session_service = InMemorySessionService()
  runner = Runner(
      app_name="langcache_demo",
      agent=agent,
      session_service=session_service,
  )

  # Create a session
  session = await session_service.create_session(
      app_name="langcache_demo",
      user_id="demo_user",
  )

  # Test queries -- the second similar query should hit the cache
  queries = [
      "What is Python programming language?",
      "Tell me about Python programming",  # Semantically similar -- should hit cache
      "How do I write a for loop in Python?",  # Different question
  ]

  for i, query in enumerate(queries, 1):
    print(f"\n{'='*60}\nQuery {i}: {query}\n{'='*60}")

    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session.id,
        new_message=content,
    ):
      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.text:
            print(f"Response: {part.text[:200]}...")
            break

  print("\n" + "=" * 60 + "\nDemo complete! Responses were cached via LangCache.")


if __name__ == "__main__":
  asyncio.run(main())

