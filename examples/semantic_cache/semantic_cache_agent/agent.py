# Copyright 2025 Google LLC
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

"""Agent definition with semantic caching enabled."""

import os

from google.adk.agents import Agent

from adk_redis.cache import create_llm_cache_callbacks
from adk_redis.cache import LLMResponseCache
from adk_redis.cache import LLMResponseCacheConfig
from adk_redis.cache import RedisVLCacheProvider
from adk_redis.cache import RedisVLCacheProviderConfig

# Import vectorizer (requires redisvl with OpenAI support)
try:
  from redisvl.utils.vectorize import OpenAITextVectorizer

  # Create vectorizer for semantic similarity
  vectorizer = OpenAITextVectorizer(
      model="text-embedding-3-small",
      api_config={"api_key": os.getenv("OPENAI_API_KEY")},
  )

  # Create cache provider
  provider = RedisVLCacheProvider(
      config=RedisVLCacheProviderConfig(
          redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
          name="adk_semantic_cache",
          ttl=3600,
          distance_threshold=0.1,
      ),
      vectorizer=vectorizer,
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
  # Fallback if redisvl is not installed
  before_model_cb = None
  after_model_cb = None

# Create the root agent with caching callbacks
root_agent = Agent(
    name="cached_assistant",
    model="gemini-2.0-flash",
    instruction="""You are a helpful assistant with semantic caching enabled.

Your responses are cached based on semantic similarity, so similar questions
will receive cached responses for faster performance.

Answer questions clearly and concisely. When asked about programming,
provide practical examples.""",
    before_model_callback=before_model_cb,
    after_model_callback=after_model_cb,
)
