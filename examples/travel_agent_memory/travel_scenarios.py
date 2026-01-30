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

"""Shared travel conversation scenarios for both examples."""

# User journey through a travel planning conversation
TRAVEL_JOURNEY = [
    # Phase 1: Initial preferences
    {
        "phase": "Setting Preferences",
        "messages": [
            "Hi! I'm planning some trips and want to share my travel preferences with you.",
            "I always prefer window seats on flights.",
            "I'm vegetarian, so please remember that for meal recommendations.",
            "I prefer boutique hotels over large chains.",
            "I have a fear of flying, so I prefer direct flights when possible.",
        ],
    },
    # Phase 2: Recall preferences
    {
        "phase": "Recalling Preferences",
        "messages": [
            "What do you remember about my travel preferences?",
            "What are my dietary restrictions?",
        ],
    },
    # Phase 3: Planning a trip
    {
        "phase": "Trip Planning",
        "messages": [
            "I'm planning a trip to Paris next month. Can you help me find flights?",
            "What kind of hotel should I look for based on my preferences?",
        ],
    },
    # Phase 4: Update preferences
    {
        "phase": "Updating Preferences",
        "messages": [
            "Actually, I've been working on my fear of flying. I'm okay with connecting flights now.",
            "I changed my mind about seats - I prefer aisle seats now for easier bathroom access.",
        ],
    },
    # Phase 5: Verify updates
    {
        "phase": "Verifying Updates",
        "messages": [
            "What seat preference do you have for me now?",
            "Am I still okay with direct flights only?",
        ],
    },
    # Phase 6: Delete preference
    {
        "phase": "Deleting Preferences",
        "messages": [
            "Actually, forget about my hotel preferences. I want to be more flexible.",
        ],
    },
    # Phase 7: Final trip planning
    {
        "phase": "Final Planning",
        "messages": [
            "Now help me plan that Paris trip with my updated preferences.",
            "What do you remember about me for this trip?",
        ],
    },
]


def get_all_messages():
    """Get all messages from the journey in order."""
    messages = []
    for phase in TRAVEL_JOURNEY:
        messages.extend(phase["messages"])
    return messages


def get_phases():
    """Get list of phase names."""
    return [phase["phase"] for phase in TRAVEL_JOURNEY]


def get_messages_by_phase(phase_name: str):
    """Get messages for a specific phase."""
    for phase in TRAVEL_JOURNEY:
        if phase["phase"] == phase_name:
            return phase["messages"]
    return []

