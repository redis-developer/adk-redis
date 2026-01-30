"""Shared conversation scenarios for memory tools comparison.

This module defines identical conversation flows used by both
tool-based and service-based examples for fair comparison.
"""

# Conversation scenarios that test different memory operations
CONVERSATION_SCENARIOS = [
    {
        "name": "Initial Introduction",
        "messages": [
            "Hi! My name is Alice and I'm a software engineer.",
            "I love Python programming and working with Redis.",
            "My favorite food is sushi, especially salmon nigiri.",
        ],
        "expected_memories": ["name: Alice", "occupation: software engineer", "favorite food: sushi"],
    },
    {
        "name": "Memory Recall",
        "messages": [
            "What do you remember about me?",
            "What's my name?",
            "What do I do for work?",
        ],
        "expected_behavior": "Should recall previously stored information",
    },
    {
        "name": "Memory Update",
        "messages": [
            "Actually, I prefer tuna nigiri over salmon now.",
            "I got promoted to senior software engineer!",
        ],
        "expected_behavior": "Should update existing memories",
    },
    {
        "name": "Explicit Memory Creation",
        "messages": [
            "Please remember that I prefer window seats on flights.",
            "Remember that my favorite color is blue.",
            "Don't forget that I'm allergic to peanuts.",
        ],
        "expected_behavior": "Should explicitly store these preferences",
    },
    {
        "name": "Memory Search",
        "messages": [
            "What are my food preferences?",
            "Tell me about my work.",
            "What do you know about my travel preferences?",
        ],
        "expected_behavior": "Should search and retrieve relevant memories",
    },
    {
        "name": "Memory Deletion",
        "messages": [
            "Forget about my food preferences.",
            "Delete what you know about my favorite color.",
        ],
        "expected_behavior": "Should delete specified memories",
    },
    {
        "name": "Verification After Deletion",
        "messages": [
            "What's my favorite food?",
            "What's my favorite color?",
        ],
        "expected_behavior": "Should not recall deleted information",
    },
]

# Test configuration
TEST_CONFIG = {
    "namespace": "comparison_test",
    "user_id": "alice_test_user",
    "api_base_url": "http://localhost:8000",
    "model": "gemini-2.0-flash-exp",
}

