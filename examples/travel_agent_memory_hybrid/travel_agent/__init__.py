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

"""Travel Agent Hybrid: Full Services + Memory Tools.

This package provides a comprehensive travel planning agent demonstrating
the HYBRID approach with both framework-managed services and LLM-controlled tools:

Framework-Managed (via main.py):
- RedisWorkingMemorySessionService (auto-summarization)
- RedisLongTermMemoryService (semantic search)

LLM-Controlled (via tools):
- SearchMemoryTool, CreateMemoryTool, UpdateMemoryTool, DeleteMemoryTool
- preload_memory, load_memory (ADK built-in)
- TavilySearchTool, ItineraryPlannerTool, CalendarExportTool

To run (MUST use main.py for services):
    cd examples/travel_agent_memory_hybrid
    python main.py

Note: Do NOT use 'adk web .' - that bypasses the Redis services.
"""

from travel_agent.agent import root_agent

__all__ = ["root_agent"]
