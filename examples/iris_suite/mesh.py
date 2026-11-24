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

"""Serve a Google ADK answer as a resumable Agent Mesh event stream."""

import os
from pathlib import Path
from uuid import UUID
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import Request
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel
from pydantic import Field
from redis_iris.agent_mesh.fastapi_sse import FastAPIRedis
from redis_iris.agent_mesh.fastapi_sse import StreamBackendDep
from redis_iris.agent_mesh.fastapi_sse import StreamWriter
import uvicorn

from adk_redis.iris import stream_adk_turn

APP_NAME = "iris_mesh_demo"
USER_ID = "local-demo"
SCOPE = "adk:local-demo"

app = FastAPI()
FastAPIRedis(app).lifespan().streams()


class Prompt(BaseModel):
  """Input for a single streamed turn."""

  text: str = Field(min_length=1, max_length=2_000)


async def produce_answer(prompt: str, writer: StreamWriter) -> None:
  """Run ADK independently of the HTTP reader and persist its text events."""
  agent = Agent(
      name="streaming_assistant",
      model=os.environ["GOOGLE_MODEL"],
      instruction="Answer clearly in a few sentences.",
  )
  async with InMemoryRunner(agent=agent, app_name=APP_NAME) as runner:
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=writer.stream_id
    )
    await stream_adk_turn(
        runner,
        writer,
        user_id=USER_ID,
        session_id=writer.stream_id,
        message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    )


@app.post("/runs", status_code=202)
async def start_run(body: Prompt, streams: StreamBackendDep) -> dict[str, str]:
  """Start one local demo turn and return its stream ID."""

  async def produce(writer: StreamWriter) -> None:
    await produce_answer(body.text, writer)

  writer = await streams.start(produce, scope=SCOPE, stream_id=uuid4().hex)
  return {"stream_id": writer.stream_id}


@app.get("/runs/{run_id}/events")
async def read_events(
    run_id: UUID, request: Request, streams: StreamBackendDep
):
  """Stream retained events after the request's Last-Event-ID, then follow."""
  return await streams.sse(run_id.hex, scope=SCOPE, request=request)


if __name__ == "__main__":
  load_dotenv(Path(__file__).with_name(".env"))
  uvicorn.run(app, host="127.0.0.1", port=8080)
