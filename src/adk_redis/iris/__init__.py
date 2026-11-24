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

"""Redis Iris runtime integrations for Google ADK.

Install `adk-redis[iris]` on Python 3.11 or later. Agent Mesh transport
dependencies are available with `adk-redis[mesh]`.
"""

from adk_redis.iris.gateway import IrisGatewayToolset
from adk_redis.iris.lens import IrisLens
from adk_redis.iris.mesh import stream_adk_turn
from adk_redis.iris.playbooks import IrisPlaybooksPlugin
from adk_redis.iris.routing import IrisIntentRouter

__all__ = [
    "IrisGatewayToolset",
    "IrisIntentRouter",
    "IrisLens",
    "IrisPlaybooksPlugin",
    "stream_adk_turn",
]
