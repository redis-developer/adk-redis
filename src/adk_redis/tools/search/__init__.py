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

"""Redis search tools for ADK using RedisVL."""

from adk_redis.tools.search._base import BaseRedisSearchTool
from adk_redis.tools.search._base import VectorizedSearchTool
from adk_redis.tools.search._config import RedisAggregatedHybridQueryConfig
from adk_redis.tools.search._config import RedisHybridQueryConfig
from adk_redis.tools.search._config import RedisRangeQueryConfig
from adk_redis.tools.search._config import RedisTextQueryConfig
from adk_redis.tools.search._config import RedisVectorQueryConfig
from adk_redis.tools.search.hybrid import RedisHybridSearchTool
from adk_redis.tools.search.range import RedisRangeSearchTool
from adk_redis.tools.search.text import RedisTextSearchTool
from adk_redis.tools.search.vector import RedisVectorSearchTool

__all__ = [
    # Base classes
    "BaseRedisSearchTool",
    "VectorizedSearchTool",
    # Search tools
    "RedisVectorSearchTool",
    "RedisHybridSearchTool",
    "RedisRangeSearchTool",
    "RedisTextSearchTool",
    # Config classes
    "RedisVectorQueryConfig",
    "RedisHybridQueryConfig",
    "RedisAggregatedHybridQueryConfig",
    "RedisRangeQueryConfig",
    "RedisTextQueryConfig",
]
