# How to Run the Travel Agent Examples

## Prerequisites

### 1. Start Redis Agent Memory Server

The examples require the Agent Memory Server running on port **8088** (not 8000):

```bash
# Check if it's running
docker ps | grep agent-memory-server

# If not running, start it
docker start agent-memory-server

# Check the logs
docker logs agent-memory-server --tail 50 -f
```

### 2. Verify Redis is Running

The Agent Memory Server needs Redis:

```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start it
redis-server --port 6379 --daemonize yes
```

## Running the Examples

### Simple Test (Recommended First)

Start with the simple test to verify everything works:

```bash
cd examples/travel_agent_memory
uv run python test_tools_simple.py
```

Expected output:
```
👤 USER: Please remember that I like pizza
🤖 AGENT: I will remember that you like pizza.

👤 USER: What do you remember about me?
🤖 AGENT: I remember that you like pizza.
```

### Full Travel Agent WITH Tools

This shows explicit memory control via tools:

```bash
uv run python travel_agent_with_tools.py
```

This runs through 16 conversation turns demonstrating:
- Creating memories (preferences)
- Searching memories (recall)
- Updating memories (changing preferences)
- Deleting memories (removing preferences)

### Travel Agent WITHOUT Tools (TODO)

This shows automatic memory via callbacks:

```bash
uv run python travel_agent_without_tools.py
```

## Monitoring Agent Memory Server

### Watch the Logs in Real-Time

Open a separate terminal and run:

```bash
docker logs agent-memory-server -f
```

You'll see:
- **Memory extraction**: When memories are extracted from conversations
- **Background tasks**: When background processing runs
- **API calls**: All HTTP requests to the server
- **Embeddings**: When text is embedded for semantic search

### Check Memory Server Health

```bash
curl http://localhost:8088/health
```

### List All Namespaces

```bash
curl http://localhost:8088/v1/namespaces
```

You should see:
- `travel_agent_with_tools`
- `test_tools_simple`
- Any other namespaces from your tests

### View Memories for a User

```bash
# List memories for traveler_alice in travel_agent_with_tools namespace
curl "http://localhost:8088/v1/namespaces/travel_agent_with_tools/users/traveler_alice/memories"
```

### View Working Memory (Session)

```bash
# Replace SESSION_ID with actual session ID from the output
curl "http://localhost:8088/v1/namespaces/travel_agent_with_tools/users/traveler_alice/sessions/SESSION_ID"
```

## Background Task Configuration

### Current Setup

The Agent Memory Server runs background tasks that:
1. **Extract memories** from working memory to long-term memory
2. **Deduplicate** similar memories
3. **Compact** old memories
4. **Clean up** expired sessions

### How Background Tasks Work

**In the WITH TOOLS example:**
- Background tasks run on the Agent Memory Server side
- The server automatically extracts memories from the session
- Frequency is controlled by the Agent Memory Server configuration

**In the WITHOUT TOOLS example (uses callbacks):**
- `before_agent` callback: Searches long-term memory and adds to context
- `after_agent` callback: Stores session to working memory
- The server then extracts to long-term memory via background tasks

### Adjusting Background Task Frequency

The background task interval is configured in the Agent Memory Server, not in the client code.

To change it, you need to modify the Agent Memory Server configuration:

```bash
# Check current server config
docker exec agent-memory-server cat /app/config.yaml

# Or check environment variables
docker exec agent-memory-server env | grep BACKGROUND
```

Common environment variables:
- `BACKGROUND_TASK_INTERVAL` - How often background tasks run (default: 60 seconds)
- `MEMORY_EXTRACTION_BATCH_SIZE` - How many sessions to process per batch
- `SESSION_TTL` - How long to keep sessions before cleanup

To run background tasks more frequently, restart the container with:

```bash
docker stop agent-memory-server
docker run -d \
  --name agent-memory-server \
  -p 8088:8088 \
  -e BACKGROUND_TASK_INTERVAL=10 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  redis/agent-memory-server:latest
```

## Differences Between Examples

### WITH Tools (Explicit Control)
- ✅ LLM decides when to create/search/update/delete memories
- ✅ Fine-grained control over memory operations
- ✅ Can see tool calls in the conversation
- ❌ LLM might forget to use tools
- ❌ More token usage (tool declarations + calls)

### WITHOUT Tools (Automatic via Callbacks)
- ✅ Automatic memory extraction (no LLM decision needed)
- ✅ Consistent memory behavior
- ✅ Less token usage
- ❌ Less control over what gets stored
- ❌ Memories extracted in batches (not immediate)

The callbacks used in the WITHOUT tools example:
```python
async def before_agent(callback_context: CallbackContext):
    """Retrieve memories before agent processes request."""
    await callback_context.search_memory()

async def after_agent(callback_context: CallbackContext):
    """Store session to memory after agent completes."""
    await callback_context.add_session_to_memory()
```

These are the same callbacks used in `/examples/redis_memory/redis_memory_agent/agent.py`!

