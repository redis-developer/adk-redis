# Copyright 2025 Google LLC
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

"""Travel Agent with Memory, Web Search, and Calendar Export.

This package provides a comprehensive travel planning agent that demonstrates
ADK-Redis capabilities:
- Two-tier memory architecture (Agent Memory Server)
- Web search with Redis caching (Tavily)
- Explicit and automatic memory tools
- Multi-user support with memory isolation

To run with ADK Web Runner:
    adk web travel_agent

To run programmatically:
    from travel_agent import root_agent
    # Use root_agent in your code
"""

from travel_agent.agent import root_agent

__all__ = ["root_agent"]

