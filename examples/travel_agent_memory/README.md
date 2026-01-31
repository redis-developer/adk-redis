# Travel Agent with Memory

A comprehensive travel planning agent demonstrating ADK-Redis integration with Redis Agent Memory Server.

## Overview

This example showcases a production-ready travel agent with:
- **Two-tier memory architecture** - Working memory + long-term memory via Agent Memory Server
- **Hybrid memory approach** - Both explicit tools (user-controlled) and automatic callbacks (framework-controlled)
- **Web search with caching** - Tavily search with Redis-backed result caching
- **Calendar integration** - Export itineraries to ICS format
- **Multi-day trip planning** - Structured itinerary generation
- **Multi-user support** - Memory isolation per user

## Quick Start

### Prerequisites

#### Option 1: Docker Compose (Recommended)

> **Important**: A recent bug fix for non-OpenAI provider support is available in the latest GitHub commit but not yet in a release. You must build Agent Memory Server from source before running Docker Compose.

**Step 1: Build Agent Memory Server from source**

**Option A: Automated setup (recommended)**

```bash
# Run the setup script from the repository root
./scripts/setup-agent-memory-server.sh
```

This script will automatically clone, build, and verify the Agent Memory Server image.

**Option B: Manual setup**

```bash
# Clone the repository
git clone https://github.com/redis/agent-memory-server.git /tmp/agent-memory-server
cd /tmp/agent-memory-server

# Build Docker image with tag 'agent-memory-server:latest-fix'
docker build -t agent-memory-server:latest-fix .

# Verify the image was built
docker images | grep agent-memory-server
# Should show: agent-memory-server   latest-fix   ...
```

**Step 2: Start the services with Docker Compose**

```bash
cd examples/travel_agent_memory
docker compose up -d
```

> **Tip**: If you used the automated setup script, it will show you the exact next steps after completion.

> **How it works**: The `docker-compose.yml` file is configured to use the locally built image `agent-memory-server:latest-fix`. Docker Compose will look for this image on your local machine (which you built in Step 1) and use it to start the container.

**What's running:**
- **Redis 8.4** on port 6379
- **Agent Memory Server** on port 8088 (using Gemini with `EXTRACTION_DEBOUNCE_SECONDS=5`)

> **Configuration**: The docker-compose.yml is pre-configured with Gemini. To use a different provider, edit the environment variables in `docker-compose.yml`:
> ```yaml
> environment:
>   - GEMINI_API_KEY=${GEMINI_API_KEY}  # Change to your provider's API key
>   - GENERATION_MODEL=gemini/gemini-2.0-flash-exp  # Change to your model
>   - EMBEDDING_MODEL=gemini/text-embedding-004  # Change to your embedding model
>   - EXTRACTION_DEBOUNCE_SECONDS=5
> ```

> **After the next release**: Once Agent Memory Server releases a new version with the bug fix, you can switch to the official image by setting the environment variable:
> ```bash
> export AGENT_MEMORY_SERVER_IMAGE=redislabs/agent-memory-server:latest
> docker compose up -d
> ```



#### Option 2: Manual Docker Setup

If you prefer to run containers manually:

> **Important**: A recent bug fix for non-OpenAI provider support is available in the latest GitHub commit but not yet in a release. Build from source to use the fix.

**Build Agent Memory Server from source:**

```bash
# Clone the repository
git clone https://github.com/redis/agent-memory-server.git /tmp/agent-memory-server
cd /tmp/agent-memory-server

# Build Docker image
docker build -t agent-memory-server:latest-fix .
```

**Start the containers:**

```bash
# 1. Start Redis 8.4
docker run -d --name redis -p 6379:6379 redis:8.4-alpine

# 2. Start Agent Memory Server
docker run -d --name agent-memory-server -p 8088:8088 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-gemini-api-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash-exp \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  -e EXTRACTION_DEBOUNCE_SECONDS=5 \
  agent-memory-server:latest-fix \
  agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
```

> **Configuration Options:**
> - **LLM Provider**: Agent Memory Server uses [LiteLLM](https://docs.litellm.ai/) and supports 100+ providers (OpenAI, Gemini, Anthropic, AWS Bedrock, Ollama, etc.). Set the appropriate environment variables for your provider (e.g., `GEMINI_API_KEY`, `GENERATION_MODEL=gemini/gemini-2.0-flash-exp`). See the [Agent Memory Server LLM Providers docs](https://redis.github.io/agent-memory-server/llm-providers/) for details.
> - **Memory Extraction Debounce**: `EXTRACTION_DEBOUNCE_SECONDS` controls how long to wait before extracting memories from a conversation (default: 300 seconds). Lower values (e.g., 5) provide faster memory extraction, while higher values reduce API calls.
> - **Embedding Models**: Agent Memory Server also uses LiteLLM for embeddings. For local/offline embeddings, use Ollama (e.g., `EMBEDDING_MODEL=ollama/nomic-embed-text`, `REDISVL_VECTOR_DIMENSIONS=768`). Note: The `redis/langcache-embed-v1` model used in the semantic_cache example is not supported by Agent Memory Server (it's RedisVL-specific). See [Embedding Providers docs](https://redis.github.io/agent-memory-server/embedding-providers/) for all options.
>
> **Using the official release**: Once the next version is released, you can use `redislabs/agent-memory-server:latest` instead of building from source.

### Setup Environment Variables

```bash
cd examples/travel_agent_memory
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY and TAVILY_API_KEY
```

### (Optional) Seed Demo User Profiles

```bash
uv run python seed_data/seed_script.py
```

This creates 3 demo users:
- **tyler** - Luxury traveler (business class, 5-star hotels, $5k-10k budget)
- **nitin** - Comfort traveler (premium economy, 3-4 star hotels, vegetarian, $2.5k-4k budget)
- **vishal** - Budget traveler (economy class, hostels, $800-1.5k budget)

### Running the Agent

**Option 1: ADK Web Runner (Recommended)**

```bash
# From the repository root
cd examples/travel_agent_memory
uv run adk web .
```

Or specify the directory directly:
```bash
# From anywhere
uv run adk web examples/travel_agent_memory
```

Then open **http://localhost:8000** in your browser.

**Web UI Features:**
- Chat interface with message history
- Events panel to inspect function calls
- Trace button for latency visualization
- Hot reload on code changes

**Option 2: Programmatic Usage**

```python
from travel_agent import root_agent
from google.adk.runners import Runner

runner = Runner(agent=root_agent)

# Run a conversation
response = runner.run("Hi, I need help planning a trip to Tokyo")
print(response.text)
```

---

## Features

### 1. Hybrid Memory Architecture

This agent uses **both** explicit and automatic memory approaches:

**Explicit Memory Tools (User-Controlled):**
- `search_memory` - Search for stored preferences
- `create_memory` - Store new preferences
- `update_memory` - Modify existing preferences
- `delete_memory` - Remove preferences

**Automatic Memory Callbacks (Framework-Controlled):**
- `load_memory` - Automatically loads relevant context before processing
- `preload_memory` - Enriches responses with user history
- `after_agent` callback - Extracts and stores memories after each turn

**Why both?**
- Explicit tools give users control ("remember this", "forget that")
- Automatic callbacks ensure nothing is missed
- Best of both worlds: transparency + seamlessness

### 2. Web Search with Redis Caching

- Tavily search integration for real-time travel information
- Results cached in Redis (1 hour TTL)
- Reduces API calls and improves response time
- Automatically disabled if `TAVILY_API_KEY` not set

### 3. Calendar Export & Itinerary Planning

- `plan_itinerary` - Create structured multi-day trip plans
- `export_to_calendar` - Generate ICS files for calendar import
- Organized by day and time with emoji categories
- Compatible with Google Calendar, Outlook, Apple Calendar

### 4. Multi-User Support

- Memory isolated per user via `user_id`
- Demo users: tyler (luxury), nitin (comfort), vishal (budget)
- Persistent preferences across sessions

---

## How It Works

### First Interaction

The agent will ask for your name/user_id on first interaction:

```
USER: "Hi, I need help planning a trip"

AGENT: "Hello! I'd be happy to help you plan your trip. To provide
       personalized recommendations and remember your preferences for
       future conversations, may I ask your name or a preferred identifier?"

USER: "I'm Sarah"

AGENT: "Great to meet you, Sarah! Let me search my memory to see if
       we've talked before... I don't have any previous conversations
       with you. How can I help you plan your trip today?"
```

### Using Demo Users

If you seeded the demo users, you can use their profiles:

```
USER: "Hi, I'm Nitin"

AGENT: "Welcome back, Nitin! I remember you prefer premium economy flights,
       3-4 star hotels, and vegetarian meals. How can I help you today?"
```

### Memory Persistence

All preferences are stored in Agent Memory Server and persist across sessions:

```
# Session 1
USER: "I'm vegetarian"
AGENT: "I'll remember that you're vegetarian for future recommendations."

# Session 2 (days later)
USER: "Recommend restaurants in Bangkok"
AGENT: "Based on your vegetarian diet, I recommend..."
```

---

## Example Interactions

### 1. Memory Management (Explicit Tools)

```
USER: "I'm vegetarian and prefer window seats"

AGENT: "I'll remember that! ✓ Stored your dietary preference (vegetarian)
       ✓ Stored your seating preference (window seats)"

USER: "What do you remember about me?"

AGENT: "Let me check... You're vegetarian and prefer window seats on flights."

USER: "Actually, forget the seating preference"

AGENT: "✓ Deleted your seating preference. I'll no longer remember that."
```

### 2. Web Search with Redis Caching

```
USER: "What are the best vegetarian restaurants in Bangkok?"

AGENT: [Uses web_search tool - first time]
       "Searching the web for current recommendations...

       Based on recent reviews, here are top vegetarian restaurants in Bangkok:
       1. Broccoli Revolution - Modern plant-based cuisine
       2. May Veggie Home - Traditional Thai vegetarian
       3. Veganerie Concept - Vegan comfort food

       [Result cached for 1 hour]"

USER: "What about vegetarian restaurants in Bangkok?" [Asked 10 minutes later]

AGENT: [Uses cached result - instant response]
       "From my recent search: Broccoli Revolution, May Veggie Home,
       and Veganerie Concept are highly rated..."
```

### 3. Multi-Day Itinerary Planning

```
USER: "Plan a 3-day trip to Paris"

AGENT: [Uses plan_itinerary tool]
       "Here's your 3-day Paris itinerary:

       Day 1: Arrival & Eiffel Tower
       • 10:00 AM - Eiffel Tower visit
       • 1:00 PM - Lunch at Le Jules Verne (vegetarian options available)
       • 3:00 PM - Seine River cruise

       Day 2: Museums & Culture
       • 9:00 AM - Louvre Museum
       • 12:30 PM - Lunch at Wild & The Moon (plant-based)
       • 3:00 PM - Musée d'Orsay

       Day 3: Montmartre & Departure
       • 10:00 AM - Sacré-Cœur Basilica
       • 12:00 PM - Lunch at Hank Vegan Burger
       • 2:00 PM - Shopping at Le Marais

       Would you like me to export this to your calendar?"
```

### 4. Calendar Export (ICS Format)

```
USER: "Yes, export it to my calendar"

AGENT: [Uses export_to_calendar tool]
       "✓ Calendar export created with 9 events!

       Here's the ICS content (copy and save as .ics file):

       BEGIN:VCALENDAR
       VERSION:2.0
       PRODID:-//ADK-Redis Travel Agent//EN
       BEGIN:VEVENT
       SUMMARY:Eiffel Tower visit
       DTSTART:20260215T100000
       DTEND:20260215T120000
       LOCATION:Eiffel Tower, Paris
       ...
       END:VEVENT
       ...
       END:VCALENDAR

       To import:
       • Google Calendar: Settings → Import & Export → Import
       • Outlook: File → Open & Export → Import/Export
       • Apple Calendar: File → Import"
```

### 5. Multi-User Support

```
# User: nitin (vegetarian, premium economy, $2.5k-4k budget)
USER: "Hi, I'm Nitin"
AGENT: "Welcome back, Nitin! I remember you prefer premium economy flights,
       3-4 star hotels, and vegetarian meals. How can I help you today?"

# User: tyler (luxury, business class, $5k-10k budget)
USER: "Hi, I'm tyler"
AGENT: "Welcome back, Tyler! I remember you prefer business class flights,
       5-star hotels with spa facilities. Planning another luxury trip?"

# User: arsene (budget, economy, $800-1.5k budget)
USER: "Hi, I'm Vishal"
AGENT: "Hey Vishal! I know you're into budget travel, hostels, and backpacking.
       What adventure are you planning next?"
```

### 6. Hybrid Memory (Automatic + Explicit)

```
# Automatic memory (via callbacks)
USER: "I'm planning a trip to Tokyo in March"

AGENT: "Tokyo in March is beautiful with cherry blossoms! What would you like to know?"
       [after_agent callback automatically stores: trip to Tokyo, March timing]

# Later session - automatic recall
USER: "What was I planning?"

AGENT: [preload_memory callback loads context]
       "You were planning a trip to Tokyo in March. Have you made any decisions?"

# Explicit memory management
USER: "Remember I need wheelchair accessible hotels"

AGENT: [Uses create_memory tool explicitly]
       "✓ Stored: Requires wheelchair accessible accommodations.
       I'll keep this in mind for all future hotel recommendations."
```

---

## Architecture

### Memory Flow

```
User Message
    ↓
[preload_memory] ← Loads relevant memories from Agent Memory Server
    ↓
[Agent Processing] ← Uses explicit memory tools if needed
    ↓
Agent Response
    ↓
[after_agent callback] ← Extracts and stores new memories
```

### Tools Available

**Memory Tools (8 total):**
1. `search_memory` - Search stored preferences
2. `create_memory` - Store new information
3. `update_memory` - Modify existing memories
4. `delete_memory` - Remove memories
5. `preload_memory` - Auto-load context (framework)
6. `load_memory` - Load specific memories (framework)
7. `export_to_calendar` - Generate ICS files
8. `plan_itinerary` - Create structured trip plans

**Optional:**
9. `web_search` - Tavily search (if TAVILY_API_KEY set)

### File Structure

```
examples/travel_agent_memory/
├── README.md                    # This file (comprehensive guide)
│
├── travel_agent/                # Main agent package
│   ├── __init__.py              # Exports root_agent
│   └── agent.py                 # Agent definition with all tools
│
├── tools/                       # Custom tools
│   ├── __init__.py
│   ├── tavily_search.py         # Web search with Redis caching
│   ├── calendar_export.py       # ICS calendar generation
│   └── itinerary_planner.py     # Multi-day trip planning
│
├── seed_data/                   # Demo user profiles
│   ├── users.json               # Tyler, Nitin, Vishal profiles
│   └── seed_script.py           # Script to populate Agent Memory Server
│
├── evaluation/                  # Testing framework
│   ├── travel_agent_eval.test.json  # Test cases
│   ├── test_config.json             # Scoring config
│   └── README.md                    # Eval documentation
│
├── .env.example                 # Environment template
└── .env                         # Your local environment (gitignored)
```

---

## Testing & Evaluation

### Run Evaluations

**Via Web UI:**
1. Start `uv run adk web .`
2. Navigate to "Evaluate" tab
3. Select test file and run

**Via CLI:**
```bash
uv run adk eval evaluation/travel_agent_eval.test.json
```

**Via pytest:**
```bash
uv run pytest evaluation/travel_agent_eval.test.json -v
```

The evaluation framework includes test cases for:
- Memory management (create, search, update, delete)
- Trip planning with itinerary generation
- Calendar export functionality

---

## Demo Users

If you run the seed script, you get 3 pre-configured users:

| User       | Style | Preferences | Budget |
|------------|-------|-------------|--------|
| **tyler**  | Luxury | Business class, 5-star hotels, spa | $5k-10k |
| **nitin**  | Comfort | Premium economy, 3-4 star, vegetarian | $2.5k-4k |
| **vishal** | Budget | Economy, hostels, backpacking | $800-1.5k |

Try: "Hi, I'm Nitin" to see personalized responses based on stored preferences.

---

## Troubleshooting

### Agent Memory Server not running

```
Error: Connection refused to http://localhost:8088
```

**Solution:** Start the services using Docker Compose:
```bash
cd examples/travel_agent_memory
docker compose up -d
```

Or manually:
```bash
# Start Redis
docker run -d --name redis -p 6379:6379 redis:8.4-alpine

# Start Agent Memory Server
docker run -d --name agent-memory-server -p 8088:8088 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e OPENAI_API_KEY=your-openai-key \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
```

> **Note**: Agent Memory Server supports multiple LLM providers via LiteLLM. See the note in the Quick Start section above for configuration details.

### Web search disabled

```
ℹ️  Web search disabled (TAVILY_API_KEY not set)
```

**Solution:** Add TAVILY_API_KEY to your .env file. The agent will still work with memory only.

### Module not found errors

```
ModuleNotFoundError: No module named 'adk_redis'
```

**Solution:** Use `uv run` to run commands:
```bash
uv run python your_script.py
# or
uv run adk web .
```

### Seed script fails with 404 errors

**Solution:** Make sure Agent Memory Server is running on port 8088. The seed script was recently updated to use the correct API endpoint (`/v1/long-term-memory/`).

---

## Key Concepts Demonstrated

1. **Two-tier memory** - Working memory (session) + long-term memory (Agent Memory Server)
2. **Hybrid approach** - Explicit tools + automatic callbacks
3. **Redis caching** - Web search results cached for performance
4. **Multi-user isolation** - Each user has separate memory namespace
5. **Tool composition** - Memory + search + calendar + planning
6. **ADK evaluation** - Test cases with scoring criteria

---

## Learn More

- [ADK-Redis Documentation](../../README.md) - Main project documentation
- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server) - Memory server documentation
- [Google ADK](https://github.com/google/adk) - ADK framework documentation

---

## License

Copyright 2025 Google LLC and Redis, Inc.

Licensed under the Apache License, Version 2.0. See [LICENSE](../../LICENSE) for details.

