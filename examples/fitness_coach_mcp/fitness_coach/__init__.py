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

"""Personal Fitness Coach with MCP Memory Tools.

This package provides a fitness coaching agent that demonstrates
MCP-based memory integration with Agent Memory Server:
- MCP tools for memory operations (search, create, edit, delete)
- Semantic memory for user profile, injuries, equipment, goals
- Episodic memory for workouts, milestones, pain reports
- Cross-session personalization and progress tracking

To run with ADK Web Runner:
    adk web fitness_coach

To run programmatically:
    from fitness_coach import root_agent
    # Use root_agent in your code
"""

from fitness_coach.agent import root_agent

__all__ = ["root_agent"]
