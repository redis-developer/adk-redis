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

"""Agent definition with LangCache semantic caching enabled.

LangCache is a managed semantic caching service by Redis. Unlike the local
RedisVL SemanticCache, LangCache handles embedding generation and vector
storage server-side -- no local vectorizer or Redis instance is required.

Sign up at https://redis.io/langcache to get a cache_id and api_key.
"""

import os

from google.adk.agents import Agent

from adk_redis.cache import create_llm_cache_callbacks
from adk_redis.cache import LangCacheCacheProvider
from adk_redis.cache import LangCacheCacheProviderConfig
from adk_redis.cache import LLMResponseCache
from adk_redis.cache import LLMResponseCacheConfig

try:
  # Create LangCache provider (managed -- no local vectorizer needed)
  provider = LangCacheCacheProvider(
      config=LangCacheCacheProviderConfig(
          cache_id=os.environ["LANGCACHE_CACHE_ID"],
          api_key=os.environ["LANGCACHE_API_KEY"],
          server_url=os.getenv(
              "LANGCACHE_SERVER_URL",
              "https://aws-us-east-1.langcache.redis.io",
          ),
          ttl=3600,
      ),
  )

  # Create LLM response cache
  llm_cache = LLMResponseCache(
      provider=provider,
      config=LLMResponseCacheConfig(
          first_message_only=True,
          include_app_name=True,
          include_user_id=True,
      ),
  )

  # Create callback functions
  before_model_cb, after_model_cb = create_llm_cache_callbacks(llm_cache)

except ImportError:
  import warnings

  warnings.warn(
      "redisvl>=0.5.0 is not installed. LangCache caching is disabled. "
      "Install with: pip install 'adk-redis[langcache]'",
      stacklevel=2,
  )
  before_model_cb = None
  after_model_cb = None

except KeyError as e:
  import warnings

  warnings.warn(
      f"Missing required environment variable {e}. "
      "Set LANGCACHE_CACHE_ID and LANGCACHE_API_KEY to enable caching.",
      stacklevel=2,
  )
  before_model_cb = None
  after_model_cb = None

# Create the root agent with caching callbacks
root_agent = Agent(
    name="langcache_assistant",
    model="gemini-2.0-flash",
    instruction="""You are a helpful assistant with LangCache semantic caching enabled.

Your responses are cached using Redis LangCache, a managed semantic caching
service. Semantically similar questions will receive cached responses for
faster performance and lower API costs.

Answer questions clearly and concisely. When asked about programming,
provide practical examples.""",
    before_model_callback=before_model_cb,
    after_model_callback=after_model_cb,
)
