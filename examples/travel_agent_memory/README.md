# Travel Agent Memory Comparison Examples

This directory contains two implementations of a travel planning agent that demonstrate different approaches to memory management with Redis Agent Memory Server and ADK.

## Overview

Both examples implement the same travel agent functionality but use different memory approaches:

1. **WITH Tools** (`travel_agent_with_tools.py`) - Explicit LLM-controlled memory operations
2. **WITHOUT Tools** (`travel_agent_without_tools.py`) - Automatic service-based memory operations

## Examples

### 1. Travel Agent WITH Memory Tools (Explicit Control)

**File:** `travel_agent_with_tools.py`

The LLM explicitly controls memory operations through tool calls:
- `MemoryPromptTool` - Enrich prompts with relevant memories
- `SearchMemoryTool` - Search for stored preferences
- `CreateMemoryTool` - Store new preferences
- `UpdateMemoryTool` - Modify existing preferences
- `DeleteMemoryTool` - Remove preferences

**Characteristics:**
- User has direct control ("remember this", "forget that")
- Agent explicitly tells user when storing/updating/deleting
- More transparent - user knows what's being remembered
- Better for privacy-sensitive applications
- Requires more LLM reasoning

**Example interaction:**
```
USER: I prefer window seats on flights.
AGENT: I'll remember that you prefer window seats. ✓ Stored your seating preference.

USER: What do you remember about me?
AGENT: Let me check... You prefer window seats on flights and you're vegetarian.
```

### 2. Travel Agent WITHOUT Memory Tools (Automatic)

**File:** `travel_agent_without_tools.py`

Memory operations happen automatically via ADK framework callbacks:
- `RedisLongTermMemoryService` - Automatic memory extraction and retrieval
- `RedisWorkingMemorySessionService` - Session management
- `before_agent_callback` - Retrieves relevant memories before processing
- `after_agent_callback` - Extracts and stores memories after processing

**Characteristics:**
- Seamless - no explicit memory commands needed
- Natural conversation flow
- Agent focuses on conversation, not memory management
- Better for chatbots and customer service
- Less user control over memory

**Example interaction:**
```
USER: I prefer window seats on flights.
AGENT: Got it! I'll keep that in mind for future flight recommendations.

USER: What do you remember about me?
AGENT: Based on our conversation, you prefer window seats and you're vegetarian.
```

## Running the Examples

### Prerequisites

1. **Start Redis Agent Memory Server:**
   ```bash
   docker run -p 8000:8000 -p 6379:6379 redis/agent-memory-server:latest
   ```

2. **Set environment variables:**
   ```bash
   export MEMORY_SERVER_URL="http://localhost:8000"
   export GOOGLE_API_KEY="your-api-key"
   ```

### Run Individual Examples

**WITH Tools:**
```bash
python travel_agent_with_tools.py
```

**WITHOUT Tools:**
```bash
python travel_agent_without_tools.py
```

### Run Comparison

Run both examples and see side-by-side comparison:
```bash
python compare_journey.py
```

This will:
- Run both approaches with the same conversation
- Show side-by-side responses
- Highlight key differences
- Generate detailed logs (`comparison_with_tools.json`, `comparison_without_tools.json`)

## Conversation Journey

The examples follow a realistic travel planning journey:

1. **Initial Preferences** - User shares seat, dietary, hotel preferences
2. **Memory Recall** - User asks what the agent remembers
3. **Preference Update** - User changes seating preference
4. **Additional Preferences** - User adds TSA PreCheck, flight preferences
5. **Personalized Recommendations** - Agent suggests flights/hotels using memories
6. **Memory Deletion** - User asks to forget TSA PreCheck
7. **Complex Planning** - Multi-city trip planning with memory context

## Key Differences

| Aspect | WITH Tools | WITHOUT Tools |
|--------|-----------|---------------|
| **Control** | Explicit user control | Automatic framework control |
| **Transparency** | Agent tells user about memory ops | Memory ops are invisible |
| **User Experience** | "Remember this", "Forget that" | Natural conversation |
| **Privacy** | User manages their data | Framework manages data |
| **Complexity** | More LLM reasoning required | Simpler agent logic |
| **Best For** | Personal assistants, note-taking | Chatbots, customer service |

## When to Use Each Approach

### Use WITH Tools (Explicit) when:
- Users need direct control over what's remembered
- Transparency is important (GDPR, privacy concerns)
- Memory operations are part of the user experience
- Building personal assistants, note-taking apps
- Users explicitly manage their data

### Use WITHOUT Tools (Automatic) when:
- Memory should be seamless and invisible
- Natural conversation flow is priority
- Building chatbots, customer service agents
- Memory is a background feature
- Simplicity over control

## Files

- `travel_scenarios.py` - Shared conversation scenarios
- `travel_agent_with_tools.py` - Tool-based implementation
- `travel_agent_without_tools.py` - Service-based implementation
- `compare_journey.py` - Comparison script
- `README.md` - This file

## Learn More

- [ADK Redis Documentation](../../README.md)
- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- [ADK Documentation](https://github.com/google/adk)

