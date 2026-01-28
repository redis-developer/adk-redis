#!/usr/bin/env python3
"""Interactive demo of the Redis Memory sample.

Shows real-time memory extraction and recall across sessions.
"""

import asyncio
import uuid

import httpx

# Configuration
ADK_URL = "http://localhost:8080"
MEMORY_SERVER_URL = "http://localhost:8000"
APP_NAME = "redis_memory_agent"
USER_ID = f"demo_user_{uuid.uuid4().hex[:8]}"
NAMESPACE = "adk_agent_memory"


# ANSI colors for visualization
class Colors:
  HEADER = "\033[95m"
  BLUE = "\033[94m"
  CYAN = "\033[96m"
  GREEN = "\033[92m"
  YELLOW = "\033[93m"
  RED = "\033[91m"
  BOLD = "\033[1m"
  END = "\033[0m"


def print_header(text):
  print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}")
  print(f"{text}")
  print(f"{'=' * 70}{Colors.END}\n")


def print_section(text):
  print(f"\n{Colors.CYAN}{Colors.BOLD}--- {text} ---{Colors.END}")


def print_user(text):
  print(f"{Colors.GREEN}User:{Colors.END} {text}")


def print_agent(text):
  print(f"{Colors.BLUE}Agent:{Colors.END} {text}")


def print_memory(text):
  print(f"{Colors.YELLOW}Memory:{Colors.END} {text}")


def print_info(text):
  print(f"{Colors.CYAN}Info: {text}{Colors.END}")


async def create_session(client):
  """Create a new session."""
  response = await client.post(
      f"{ADK_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
      json={},
      timeout=30.0,
  )
  response.raise_for_status()
  return response.json().get("id")


async def send_message(client, session_id, message):
  """Send a message to the agent via SSE and get response."""
  async with client.stream(
      "POST",
      f"{ADK_URL}/run_sse",
      json={
          "app_name": APP_NAME,
          "user_id": USER_ID,
          "session_id": session_id,
          "new_message": {"role": "user", "parts": [{"text": message}]},
      },
      timeout=60.0,
  ) as response:
    response.raise_for_status()
    agent_response = ""
    async for line in response.aiter_lines():
      if line.startswith("data: "):
        try:
          import json

          data = json.loads(line[6:])
          content = data.get("content", {})
          parts = content.get("parts", [])
          for part in parts:
            if "text" in part:
              agent_response = part["text"]
        except Exception:
          pass
    return agent_response if agent_response else "(no response)"


async def get_working_memory(client, session_id):
  """Get working memory state from memory server."""
  try:
    response = await client.get(
        f"{MEMORY_SERVER_URL}/v1/working-memory/{session_id}",
        params={"namespace": NAMESPACE, "user_id": USER_ID},
        timeout=10.0,
    )
    if response.status_code == 200:
      return response.json()
  except Exception:
    pass
  return None


async def get_long_term_memories(client):
  """Get long-term memories from memory server."""
  try:
    response = await client.post(
        f"{MEMORY_SERVER_URL}/v1/long-term-memory/search",
        json={
            "text": "user",
            "namespace": {"eq": NAMESPACE},
            "user_id": {"eq": USER_ID},
            "limit": 20,
        },
        timeout=10.0,
    )
    if response.status_code == 200:
      return response.json().get("memories", [])
  except Exception:
    pass
  return []


async def show_memory_state(client, session_id):
  """Display current memory state."""
  print_section("Current Memory State")

  # Working memory
  wm = await get_working_memory(client, session_id)
  if wm:
    messages = wm.get("messages", [])
    memories = wm.get("memories", [])
    print(
        f"  Working Memory: {len(messages)} messages, {len(memories)} attached"
        " memories"
    )

  # Long-term memory
  ltm = await get_long_term_memories(client)
  print(f"  Long-Term Memory: {len(ltm)} facts stored")
  if ltm:
    for i, mem in enumerate(ltm[:5], 1):
      text = mem.get("text", "")[:60]
      print(f"    {i}. {text}...")


async def run_demo():
  print_header("REDIS MEMORY DEMO (adk-redis)")
  print(
      f"""
This demo shows the two-tier memory architecture in action:
  - Tier 1: Working Memory (session messages, auto-summarization)
  - Tier 2: Long-Term Memory (extracted facts, semantic search)

User ID: {USER_ID}
Namespace: {NAMESPACE}
"""
  )

  async with httpx.AsyncClient() as client:
    # Session 1: Share personal information
    session1 = await create_session(client)
    print_header("SESSION 1: Sharing Information")
    print_info(f"Session ID: {session1[:8]}...")

    conversations = [
        ("Hi! My name is Alex and I work as a data scientist at TechCorp.", 3),
        ("I've been working with machine learning for about 5 years now.", 3),
        ("My favorite frameworks are PyTorch and scikit-learn.", 3),
        ("I have two cats named Pixel and Binary.", 3),
        ("I'm currently working on a recommendation system project.", 3),
    ]

    for message, delay in conversations:
      print_user(message)
      response = await send_message(client, session1, message)
      print_agent(response[:150] + "..." if len(response) > 150 else response)
      await show_memory_state(client, session1)
      print_info(f"Waiting {delay}s for memory extraction...")
      await asyncio.sleep(delay)

    # Wait for final extraction
    print_section("Waiting for Memory Extraction")
    print_info("Waiting 10 seconds for background extraction to complete...")
    for i in range(10, 0, -1):
      print(f"\r  {i} seconds remaining...", end="", flush=True)
      await asyncio.sleep(1)
    print("\r  Done!                    ")

    await show_memory_state(client, session1)

    # Session 2: Test memory recall in a NEW session
    session2 = await create_session(client)
    print_header("SESSION 2: Testing Memory Recall (NEW SESSION)")
    print_info(f"Session ID: {session2[:8]}...")
    print_info("This is a BRAND NEW session - testing if memories persist!")

    recall_questions = [
        "What do you remember about me?",
        "What's my job?",
        "What are my cats' names?",
        "What project am I working on?",
    ]

    for question in recall_questions:
      print_user(question)
      response = await send_message(client, session2, question)
      print_agent(response[:200] + "..." if len(response) > 200 else response)
      print()
      await asyncio.sleep(1)

    # Final summary
    print_header("DEMO COMPLETE")
    await show_memory_state(client, session2)
    print(
        """
Summary:
  - Session 1: Shared 5 facts about the user
  - Session 2: Successfully recalled memories from Session 1
  - Long-term memories persist across sessions!
"""
    )


if __name__ == "__main__":
  asyncio.run(run_demo())
