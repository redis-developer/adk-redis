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

"""Memory backend names."""

from __future__ import annotations

from typing import Literal
import warnings

REDIS_AGENT_MEMORY_BACKEND: Literal["redis-agent-memory"] = "redis-agent-memory"
OPENSOURCE_AGENT_MEMORY_BACKEND: Literal["opensource-agent-memory"] = (
    "opensource-agent-memory"
)

MemoryBackendName = Literal[
    "redis-agent-memory",
    "opensource-agent-memory",
]


def warn_if_deprecated_backend(backend: str, *, stacklevel: int = 3) -> None:
  """Warn when the deprecated self-hosted Agent Memory Server is selected.

  Args:
      backend: The configured memory backend name.
      stacklevel: Stack level passed to ``warnings.warn``, so the warning
          points at the caller that constructed the service or tool.
  """
  if backend == OPENSOURCE_AGENT_MEMORY_BACKEND:
    warnings.warn(
        "The opensource-agent-memory backend is deprecated and will be"
        " removed in 0.2.0. Use backend='redis-agent-memory' with Redis"
        " Agent Memory.",
        DeprecationWarning,
        stacklevel=stacklevel,
    )
