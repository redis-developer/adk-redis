# Travel Agent - Quick Start Guide

**One comprehensive travel agent example with memory, web search, and personalized recommendations.**

---

## Prerequisites

1. **Start Agent Memory Server:**
   ```bash
   docker run -p 8088:8088 -p 6379:6379 redis/agent-memory-server:latest
   ```

2. **Set up environment variables:**
   ```bash
   cd examples/travel_agent_memory
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY and TAVILY_API_KEY
   ```

3. **(Optional) Seed demo user profiles:**
   ```bash
   cd examples/travel_agent_memory
   uv run python seed_data/seed_script.py
   ```

   This creates 3 demo users:
   - **tyler** - Luxury traveler (business class, 5-star hotels, $5k-10k budget)
   - **nitin** - Comfort traveler (premium economy, 3-4 star hotels, vegetarian, $2.5k-4k budget)
   - **arsene** - Budget traveler (economy class, hostels, $800-1.5k budget)

---

## Running the Agent

### Option 1: ADK Web Runner (Recommended)

```bash
cd examples/travel_agent_memory
adk web travel_agent
```

Then open http://localhost:8000 in your browser.

**Features:**
- Chat interface with message history
- Events panel to inspect function calls
- Trace button for latency visualization
- Hot reload on code changes

### Option 2: Programmatic Usage

```python
from travel_agent import root_agent
from google.adk.runners import Runner

runner = Runner(agent=root_agent)

# Run a conversation
response = runner.run("Hi, I need help planning a trip to Tokyo")
print(response.text)
```

---

## How It Works

### First Interaction

The agent will ask for your name/user_id on first interaction:

```
USER: "Hi, I need help planning a trip"
AGENT: "Hello! I'd be happy to help you plan your trip. To provide 
       personalized recommendations and remember your preferences for 
       future conversations, may I ask your name or a preferred identifier?"

USER: "nitin"
AGENT: "Great to meet you, Nitin! Let me search my memory to see if 
       we've talked before..."
```

### Using Demo Users

If you seeded the demo users, you can use their profiles:

```
USER: "Hi, I'm tyler"
AGENT: "Welcome back, Tyler! I remember you prefer luxury hotels with 
       spa facilities and business class flights. How can I help you today?"
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

## Agent Capabilities

### 1. Memory Management

**Explicit Tools (User-Controlled):**
- `search_memory` - Find stored preferences
- `create_memory` - Store new preferences
- `update_memory` - Modify existing preferences
- `delete_memory` - Remove preferences

**Automatic Tools (Framework-Controlled):**
- `load_memory` - Automatically load relevant context
- `preload_memory` - Enrich responses with user history

### 2. Web Search (if TAVILY_API_KEY is set)

- `web_search` - Search for current travel information
- Results cached in Redis (1 hour TTL)
- Use for weather, events, restrictions, prices

### 3. Personalization

- Searches memories before making recommendations
- References past preferences
- Learns from each conversation
- Provides tailored suggestions

---

## File Structure

```
examples/travel_agent_memory/
├── travel_agent/              # Main agent package
│   ├── __init__.py            # Exports root_agent
│   └── agent.py               # Agent definition with all tools
├── tools/                     # Custom tools
│   ├── __init__.py
│   └── tavily_search.py       # Web search with Redis caching
├── seed_data/                 # Demo user profiles
│   ├── users.json             # Tyler, Nitin, Arsene profiles
│   └── seed_script.py         # Script to populate Agent Memory Server
├── .env.example               # Environment template
├── .env                       # Your local environment (gitignored)
└── QUICKSTART.md              # This file
```

---

## Troubleshooting

### Agent Memory Server not running

```
Error: Connection refused to http://localhost:8088
```

**Solution:** Start Agent Memory Server:
```bash
docker run -p 8088:8088 -p 6379:6379 redis/agent-memory-server:latest
```

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
uv run adk web travel_agent
```

---

## Next Steps

- See [FEATURE_PARITY_ANALYSIS.md](./FEATURE_PARITY_ANALYSIS.md) for comparison with AutoGen
- See [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) for future enhancements
- See [RUNNING.md](./RUNNING.md) for detailed documentation

