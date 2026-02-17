#!/usr/bin/env python3
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

"""Seed Agent Memory Server with demo user profiles.

This script loads user profiles from users.json and populates the Agent Memory
Server with their preferences. This allows you to test the travel agent with
pre-configured user profiles.

Usage:
    python seed_script.py

Environment variables:
    MEMORY_SERVER_URL: Agent Memory Server URL (default: http://localhost:8088)
"""

import asyncio
import json
import os
from pathlib import Path

import httpx


async def seed_user_memories(
    user_id: str,
    preferences: list[str],
    namespace: str = "travel_agent",
    base_url: str = "http://localhost:8088",
):
  """Seed memories for a user.

  Args:
      user_id: User identifier
      preferences: List of preference strings to store
      namespace: Memory namespace
      base_url: Agent Memory Server URL
  """
  async with httpx.AsyncClient() as client:
    success_count = 0
    fail_count = 0

    for idx, pref in enumerate(preferences):
      # Create memory record with required fields
      memory_record = {
          "id": f"{user_id}_pref_{idx}",  # Required: unique ID for deduplication
          "text": pref,  # Required: the actual memory text
          "user_id": user_id,  # Optional: for user isolation
          "namespace": namespace,  # Optional: for namespace isolation
      }

      # Wrap in the expected payload format
      payload = {
          "memories": [memory_record],
          "deduplicate": True,
      }

      try:
        response = await client.post(
            f"{base_url}/v1/long-term-memory/",
            json=payload,
            timeout=10.0,
        )

        if response.status_code in (200, 201):
          print(f"  ✅ {pref}")
          success_count += 1
        else:
          print(f"  ❌ Failed ({response.status_code}): {pref}")
          print(f"     Response: {response.text}")
          fail_count += 1
      except Exception as e:
        print(f"  ❌ Error: {pref} - {e}")
        fail_count += 1

    return success_count, fail_count


async def main():
  """Load users.json and seed all users."""
  # Get configuration
  base_url = os.getenv("MEMORY_SERVER_URL", "http://localhost:8088")
  namespace = os.getenv("NAMESPACE", "travel_agent_memory_hybrid")

  # Load users file
  users_file = Path(__file__).parent / "users.json"

  if not users_file.exists():
    print(f"❌ Error: {users_file} not found")
    return

  with open(users_file) as f:
    users = json.load(f)

  # Display header
  print("=" * 80)
  print("SEEDING DEMO USERS TO AGENT MEMORY SERVER")
  print("=" * 80)
  print(f"Memory Server: {base_url}")
  print(f"Namespace: {namespace}")
  print(f"Users to seed: {len(users)}")
  print("=" * 80)
  print()

  # Seed each user
  total_success = 0
  total_fail = 0

  for user_id, data in users.items():
    print(f"👤 Seeding user: {data['name']} ({user_id})")
    print(f"   Preferences: {len(data['preferences'])}")

    success, fail = await seed_user_memories(
        user_id=user_id,
        preferences=data["preferences"],
        namespace=namespace,
        base_url=base_url,
    )

    total_success += success
    total_fail += fail
    print()

  # Display summary
  print("=" * 80)
  print("SEEDING COMPLETE")
  print("=" * 80)
  print(f"✅ Successfully seeded: {total_success} preferences")
  if total_fail > 0:
    print(f"❌ Failed: {total_fail} preferences")
  print()
  print("To use these users in the travel agent, the agent will prompt you for")
  print("your name/user_id on first interaction. Enter one of:")
  print("  - tyler")
  print("  - nitin")
  print("  - arsene")
  print()
  print("Or enter a new name to create a fresh user profile.")
  print("=" * 80)


if __name__ == "__main__":
  asyncio.run(main())
