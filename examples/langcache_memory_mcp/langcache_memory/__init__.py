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

"""Memory agent backed by the langcache (Redis Agent Memory) MCP server.

Demonstrates driving the langcache memory-dataplane MCP tools from an ADK agent
over streamable HTTP — the managed-plane counterpart to the open-source Agent
Memory Server used by ``examples/fitness_coach_mcp``.

To run with ADK Web Runner:
    adk web langcache_memory

To run programmatically:
    from langcache_memory import root_agent
"""

from langcache_memory.agent import root_agent

__all__ = ["root_agent"]
