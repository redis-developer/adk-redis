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

"""Deprecated module path for the Redis session memory service.

This module was renamed to :mod:`adk_redis.sessions.session_memory`. It is
retained as a compatibility shim that re-exports the public classes and will
be removed in 0.1.0. Import from ``adk_redis.sessions.session_memory`` or the
top-level ``adk_redis`` package instead.
"""

from __future__ import annotations

import warnings

from adk_redis.sessions.session_memory import RedisSessionMemoryService
from adk_redis.sessions.session_memory import RedisSessionMemoryServiceConfig
from adk_redis.sessions.session_memory import RedisWorkingMemorySessionService
from adk_redis.sessions.session_memory import (
    RedisWorkingMemorySessionServiceConfig,
)

warnings.warn(
    "adk_redis.sessions.working_memory is deprecated; import from "
    "adk_redis.sessions.session_memory (or adk_redis). This module path will "
    "be removed in 0.1.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "RedisSessionMemoryService",
    "RedisSessionMemoryServiceConfig",
    "RedisWorkingMemorySessionService",
    "RedisWorkingMemorySessionServiceConfig",
]
