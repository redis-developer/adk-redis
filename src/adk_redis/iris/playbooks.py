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

"""Add Redis Agent Playbooks context to models in an ADK application."""

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.plugins.base_plugin import BasePlugin
from redis_iris.agent_playbooks import AgentPlaybooks
from redis_iris.agent_playbooks.hooks import PlaybookHooks


class IrisPlaybooksPlugin(BasePlugin):
  """Append published FAQs and the selected Skill before each model request.

  Register this plugin through `google.adk.apps.App.plugins`. Retrieval uses
  the message that started the current invocation, including in tool rounds.
  The SDK hooks own retrieval policy, skill selection, and error handling.

  Args:
      hooks: Configured SDK hooks with caller-managed client lifetime. If
          omitted, use the Iris environment and the SDK's default policy.
      name: Unique ADK plugin name.
  """

  def __init__(
      self, hooks: PlaybookHooks | None = None, *, name: str = "iris_playbooks"
  ) -> None:
    super().__init__(name=name)
    self._hooks = hooks

  async def before_model_callback(
      self, *, callback_context: CallbackContext, llm_request: LlmRequest
  ) -> None:
    """Append published Playbooks context to the current model request."""
    content = callback_context.user_content
    if content is None:
      return
    message = "\n".join(
        part.text
        for part in content.parts or []
        if part.text and not part.thought
    )
    if not message.strip():
      return
    user_id = callback_context.user_id
    session_id = callback_context.session.id
    if self._hooks is None:
      async with AgentPlaybooks.from_env() as playbook:
        guidance = await playbook.hooks().abefore(
            message, owner=user_id, session=session_id
        )
    else:
      guidance = await self._hooks.abefore(
          message, owner=user_id, session=session_id
      )
    if guidance:
      llm_request.append_instructions([guidance])
