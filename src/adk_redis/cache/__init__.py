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

"""Semantic caching for ADK agents using Redis."""

from .callbacks import create_llm_cache_callbacks, create_tool_cache_callbacks
from .llm_cache import LLMResponseCache, LLMResponseCacheConfig
from ._provider import (
    BaseCacheProvider,
    CacheEntry,
    RedisVLCacheProvider,
    RedisVLCacheProviderConfig,
)
from .tool_cache import ToolCache, ToolCacheConfig

__all__ = [
    "BaseCacheProvider",
    "CacheEntry",
    "RedisVLCacheProvider",
    "RedisVLCacheProviderConfig",
    "LLMResponseCache",
    "LLMResponseCacheConfig",
    "ToolCache",
    "ToolCacheConfig",
    "create_llm_cache_callbacks",
    "create_tool_cache_callbacks",
]
