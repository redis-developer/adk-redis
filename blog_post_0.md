# Give Your AI Agents a Brain with Redis

## How `adk-redis` Brings Persistent Memory, Semantic Search, and Caching to Google's Agent Development Kit

AI agents are only as useful as what they can remember. An agent that forgets your name between sessions, re-fetches the same data on every call, or can't search its own knowledge base isn't really an agent. It's a stateless function with a chat interface.

Google's Agent Development Kit (ADK) provides strong abstractions for building agents, but it leaves a critical question unanswered out of the box. Where does the state actually live? ADK defines interfaces like `BaseMemoryService` and `BaseSessionService`, but the default implementations store everything in memory. Restart the process, and everything is gone.

`adk-redis` is a Python package that fills this gap. It implements ADK's core interfaces using Redis as the storage backbone, giving your agents persistent memory, intelligent session management, production-grade search, and semantic caching. The result is that you can go from a toy demo to a production-ready agent by swapping in a few Redis-backed services, without changing your agent logic at all.

This post walks through the full surface area of `adk-redis`. We will cover its two-tier memory architecture, the four search tools it provides for RAG, how semantic caching can cut your LLM costs, and the three distinct approaches for integrating memory into your agents. Along the way, we will build up from simple examples to a fully wired travel planning agent.

## What `adk-redis` Actually Provides

Before diving into implementation, it helps to see the full landscape. The package is organized around four pillars.

**Memory Services** implement ADK's `BaseMemoryService`. This is long-term memory. The service connects to the Redis Agent Memory Server, which handles semantic search, automatic fact extraction, and recency-boosted retrieval across all of your agent's past conversations.

**Session Services** implement ADK's `BaseSessionService`. This is working memory. Sessions store the current conversation, manage session state, and automatically summarize older messages when the context window gets too large.

**Search Tools** wrap RedisVL (the Redis Vector Library) into ADK-compatible tools that your agent's LLM can call directly. There are four variants covering vector search, hybrid search, text search, and range search.

**Semantic Caching** intercepts LLM calls and tool executions, checking whether a semantically similar prompt has been seen before. If so, it returns the cached response instead of making a new API call. This works through ADK's callback system, so enabling it requires no changes to your agent's core logic.

The package is modular. You install only what you need.

```bash
pip install adk-redis[memory]     # Memory and session services
pip install adk-redis[search]     # Search tools via RedisVL
pip install adk-redis[langcache]  # Managed semantic caching
pip install adk-redis[all]        # Everything
```

## The Two-Tier Memory Architecture

The central design idea behind `adk-redis` is a two-tier memory system that mirrors how human memory works. There is a fast, limited working memory for the current conversation, and a slower, persistent long-term memory for facts and preferences that should survive across sessions.

### Tier 1 (Working Memory via `RedisWorkingMemorySessionService`)

Working memory handles the current session. Every message exchanged between the user and the agent is stored in the Redis Agent Memory Server. When the conversation grows long enough to approach the model's context window limit, the service automatically summarizes older messages, compressing them into a summary while preserving the most recent exchanges in full.

This is a surprisingly important feature. Without it, you face a hard tradeoff. Either you truncate old messages and lose context, or you send the full conversation and hit token limits (and costs). Auto-summarization gives you a middle path.

Here is how you configure it.

```python
from adk_redis.sessions import (
    RedisWorkingMemorySessionService,
    RedisWorkingMemorySessionServiceConfig,
)

session_config = RedisWorkingMemorySessionServiceConfig(
    api_base_url="http://localhost:8088",
    default_namespace="my_app",
    model_name="gpt-4o",
    context_window_max=8000,
)
session_service = RedisWorkingMemorySessionService(config=session_config)
```

The `context_window_max` parameter is what triggers summarization. When the token count of stored messages crosses this threshold, the Agent Memory Server uses the model specified in `model_name` to summarize older turns. The `default_namespace` isolates your application's data from other applications sharing the same Redis instance.

Under the hood, the session service implements all of ADK's required methods. `create_session`, `get_session`, `list_sessions`, `delete_session`, and `append_event`. The `append_event` method is particularly worth noting. Rather than re-sending the entire conversation on every turn, it uses an incremental append API, sending only the new message. This keeps network overhead proportional to the message size, not the conversation length.

### Tier 2 (Long-Term Memory via `RedisLongTermMemoryService`)

Long-term memory is where the real intelligence lives. After each conversation (or on a configurable debounce), the Agent Memory Server extracts structured information from the dialogue. "The user prefers window seats." "The user is allergic to shellfish." "The user visited Tokyo last March." These extracted memories are embedded as vectors and stored in Redis, where they become searchable across all past sessions.

```python
from adk_redis.memory import (
    RedisLongTermMemoryService,
    RedisLongTermMemoryServiceConfig,
)

memory_config = RedisLongTermMemoryServiceConfig(
    api_base_url="http://localhost:8088",
    default_namespace="my_app",
    extraction_strategy="discrete",
    recency_boost=True,
    semantic_weight=0.7,
    recency_weight=0.3,
)
memory_service = RedisLongTermMemoryService(config=memory_config)
```


The `extraction_strategy` parameter controls how the server breaks down conversations into storable facts. The `"discrete"` strategy extracts individual facts as separate memories, which makes them independently searchable. Other options include `"summary"` (a narrative summary of the conversation) and `"preferences"` (focused on user preferences).

Recency boosting deserves a closer look. When searching memories, raw semantic similarity alone often isn't enough. A user might have said "I love Italian food" three years ago, and "Actually, I've been getting into Japanese cuisine lately" last week. Both are semantically relevant to a query about food preferences, but the recent one matters more.

The recency boosting system addresses this by combining two scores. The `semantic_weight` controls how much the vector similarity matters, while `recency_weight` controls how much recency matters. Within the recency score itself, `freshness_weight` favors memories that were recently accessed, and `novelty_weight` favors memories that were recently created. The `half_life_last_access_days` and `half_life_created_days` parameters control how quickly each signal decays. A half-life of 7 days means that a memory's freshness score drops to 50% after a week of not being accessed.

This is a thoughtful design. It avoids the common failure mode of semantic search systems that return stale information with high confidence.

### Wiring Both Tiers Together

With both services configured, you connect them to an ADK `Runner`.

```python
from google.adk import Agent
from google.adk.runners import Runner

agent = Agent(
    name="memory_agent",
    model="gemini-2.5-flash",
    instruction="You are a helpful assistant with long-term memory.",
)

runner = Runner(
    agent=agent,
    app_name="my_app",
    session_service=session_service,
    memory_service=memory_service,
)
```

The flow is now automatic. Messages are stored in working memory as the conversation happens. When the agent finishes a turn, a callback can trigger `add_session_to_memory()`, which pushes the conversation to the Agent Memory Server for background extraction. On subsequent sessions, the memory service's `search_memory` method retrieves relevant facts from across all past conversations.


## Search Tools for RAG

Memory services handle what the agent remembers from past conversations. But what about external knowledge? Product catalogs, documentation, knowledge bases? This is the domain of retrieval-augmented generation (RAG), and `adk-redis` provides four search tools that plug directly into ADK's tool system.

Each tool wraps a RedisVL query type and exposes itself as a function the LLM can call. The LLM sees a function declaration with a `query` parameter, decides when to use it, and gets back structured results.

### RedisVectorSearchTool

The most straightforward option. It embeds the query using a vectorizer, performs K-nearest-neighbor search against a Redis index, and returns the top results.

```python
from redisvl.index import SearchIndex
from redisvl.utils.vectorize import HFTextVectorizer
from adk_redis.tools import RedisVectorSearchTool, RedisVectorQueryConfig

vectorizer = HFTextVectorizer(model="redis/langcache-embed-v2")
index = SearchIndex.from_existing("products", redis_url="redis://localhost:6379")

search_tool = RedisVectorSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisVectorQueryConfig(
        vector_field_name="embedding",
        return_fields=["name", "description", "price"],
        num_results=5,
    ),
    name="search_product_catalog",
    description="Find products by semantic similarity to a description.",
)
```

The `name` and `description` parameters matter more than they might seem. These are what the LLM reads to decide whether and when to call the tool. A vague description like "search documents" will lead to the LLM calling it at the wrong times. A specific one like "Find products by semantic similarity to a description" gives the LLM the context it needs.

### RedisHybridSearchTool

Hybrid search combines vector similarity with BM25 keyword matching. This is valuable when queries contain specific terms (product IDs, technical acronyms, exact names) that semantic search alone might miss.

The tool auto-detects whether your Redis server and RedisVL version support native hybrid search (Redis 8.4+ with RedisVL 0.13+). If they do, it uses the server-side `FT.HYBRID` command. If not, it falls back to a client-side aggregation approach. This version detection happens at initialization, so you don't need to think about it.

```python
from adk_redis.tools import RedisHybridSearchTool, RedisHybridQueryConfig

hybrid_tool = RedisHybridSearchTool(
    index=index,
    vectorizer=vectorizer,
    config=RedisHybridQueryConfig(
        text_field_name="content",
        combination_method="LINEAR",
        linear_alpha=0.7,
    ),
    name="search_legal_documents",
    description="Search legal documents using both semantic and keyword matching.",
)
```

### RedisTextSearchTool and RedisRangeSearchTool

`RedisTextSearchTool` performs pure BM25 keyword search. No embeddings, no vectorizer needed. It is the right choice when the query is about exact terms, error messages, or API names.

`RedisRangeSearchTool` is a less common but useful variant. Instead of returning the top-K results, it returns all documents within a distance threshold. This is useful for exhaustive retrieval, such as "find everything related to authentication in our documentation," where you want comprehensive coverage rather than a ranked list.

Here is a concrete example from the `redis_search_tools` example in the repo, which wires all three search modalities into a single agent.

```python
from adk_redis.tools import (
    RedisVectorSearchTool, RedisVectorQueryConfig,
    RedisTextSearchTool, RedisTextQueryConfig,
    RedisRangeSearchTool, RedisRangeQueryConfig,
)

tools = [
    RedisVectorSearchTool(
        name="semantic_search",
        description="Semantic similarity search for conceptual queries.",
        index=index, vectorizer=vectorizer,
        config=RedisVectorQueryConfig(num_results=5),
        return_fields=["title", "content", "category"],
    ),
    RedisTextSearchTool(
        name="keyword_search",
        description="Keyword search for exact terms and phrases.",
        index=index,
        config=RedisTextQueryConfig(
            text_field_name="content", text_scorer="BM25STD"
        ),
        return_fields=["title", "content", "category"],
    ),
    RedisRangeSearchTool(
        name="range_search",
        description="Returns ALL documents within a semantic distance threshold.",
        index=index, vectorizer=vectorizer,
        config=RedisRangeQueryConfig(distance_threshold=0.5),
        return_fields=["title", "content", "category"],
    ),
]

agent = Agent(
    model="gemini-2.5-flash",
    name="search_agent",
    instruction=(
        "You have three search tools. Use semantic_search for conceptual "
        "queries, keyword_search for exact terms, range_search for exhaustive "
        "retrieval."
    ),
    tools=tools,
)
```

The instruction prompt is doing real work here. It teaches the LLM when to use each tool and what to expect from each. This kind of prompt engineering is not optional. Without it, the LLM will default to calling whichever tool appears first or whichever has the most generic description.

## Semantic Caching

LLM API calls are slow and expensive. If your agent handles support queries, a significant fraction of incoming questions will be semantically similar. "How do I reset my password?" and "I need to change my password" should produce the same response, and there is no reason to pay for two LLM calls.

`adk-redis` provides semantic caching at two levels, LLM response caching and tool result caching, both backed by Redis.

### LLM Response Cache

The LLM cache intercepts calls to the language model through ADK's callback system. Before each model call, it checks whether a semantically similar prompt already exists in Redis. If it does, it returns the cached response immediately, skipping the LLM entirely. If it doesn't, it lets the call proceed and stores the response for future lookups.

```python
from redisvl.utils.vectorize import HFTextVectorizer
from adk_redis.cache import (
    RedisVLCacheProvider, RedisVLCacheProviderConfig,
    LLMResponseCache, LLMResponseCacheConfig,
    create_llm_cache_callbacks,
)

vectorizer = HFTextVectorizer(model="redis/langcache-embed-v1")

provider = RedisVLCacheProvider(
    config=RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379",
        name="my_llm_cache",
        ttl=3600,
        distance_threshold=0.1,
    ),
    vectorizer=vectorizer,
)

llm_cache = LLMResponseCache(
    provider=provider,
    config=LLMResponseCacheConfig(
        first_message_only=True,
        include_app_name=True,
        include_user_id=True,
    ),
)

before_cb, after_cb = create_llm_cache_callbacks(llm_cache)

agent = Agent(
    name="cached_agent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    before_model_callback=before_cb,
    after_model_callback=after_cb,
)
```

A few design decisions are worth noting here.

The `distance_threshold` parameter (set to 0.1 in this example) controls how similar two prompts need to be for a cache hit. A value of 0.0 means exact match only. A value of 0.1 allows small variations in phrasing. Going much higher risks returning cached responses for genuinely different questions. Tuning this threshold is application-specific and worth experimenting with.

The `first_message_only` option is a practical default. In a multi-turn conversation, later messages depend heavily on prior context, making semantic cache hits unreliable. Caching only the first message (which is typically a standalone question) avoids returning contextually wrong responses.

The cache is also smart about what it does *not* cache. Function call responses (where the LLM is invoking a tool) are skipped, as are error responses. This prevents caching intermediate steps that shouldn't be reused.

### Managed Caching with LangCache

If you'd rather not manage your own Redis instance and embedding model for caching, `adk-redis` also supports LangCache, a managed semantic caching service from Redis. With LangCache, embeddings are generated server-side, so you don't need a local vectorizer at all.

```python
from adk_redis.cache import LangCacheProvider, LangCacheProviderConfig

provider = LangCacheProvider(
    config=LangCacheProviderConfig(
        cache_id="your-cache-id",
        api_key="your-api-key",
        ttl=3600,
    )
)
```

The same `LLMResponseCache` and `ToolCache` classes work with either provider. You just swap the backend.

### Tool Result Cache

The tool cache follows the same pattern but for tool executions rather than LLM calls. If your agent calls an external API with the same arguments repeatedly, the tool cache can short-circuit the call and return the cached result.

```python
from adk_redis.cache import ToolCache, ToolCacheConfig, create_tool_cache_callbacks

tool_cache = ToolCache(
    provider=provider,
    config=ToolCacheConfig(
        tool_names={"web_search", "get_weather"},
    ),
)

before_tool_cb, after_tool_cb = create_tool_cache_callbacks(tool_cache)
```

The `tool_names` set lets you specify exactly which tools should be cached. This is important because not all tools are idempotent. You probably want to cache `get_weather` (same city, same hour, same result) but not `send_email` (same arguments, but each call should actually execute).

## Three Ways to Integrate Memory

One of the more interesting design decisions in `adk-redis` is that it offers three distinct approaches for connecting agents to memory. Each approach has different tradeoffs around control, complexity, and standardization.

### Approach 1. ADK Services (Framework-Managed)

This is what we covered in the two-tier memory section. You configure `RedisWorkingMemorySessionService` and `RedisLongTermMemoryService`, pass them to the `Runner`, and the framework handles everything automatically. Memory extraction happens in the background. Search happens before each agent turn. The agent code itself never directly interacts with memory.

This approach is the simplest to implement and the hardest to customize. The agent has no explicit control over *what* gets stored or *when* it searches. It is best for applications where you want memory to be invisible infrastructure.

### Approach 2. REST Tools (LLM-Controlled)

Instead of (or in addition to) framework-managed services, you can give the agent explicit memory tools. These are ADK tools that the LLM calls like any other function.

```python
from adk_redis.tools.memory import (
    SearchMemoryTool, CreateMemoryTool,
    UpdateMemoryTool, DeleteMemoryTool,
    MemoryToolConfig,
)

memory_config = MemoryToolConfig(
    api_base_url="http://localhost:8088",
    default_namespace="my_app",
    recency_boost=True,
)

tools = [
    SearchMemoryTool(config=memory_config),
    CreateMemoryTool(config=memory_config),
    UpdateMemoryTool(config=memory_config),
    DeleteMemoryTool(config=memory_config),
]
```

With this approach, the LLM decides when to search memory, what to store, and what to update. The agent prompt needs to instruct the LLM on memory management strategy. This requires more prompt engineering, but it gives the agent genuine autonomy over its own memory.

The travel agent example in the repo uses a hybrid of both approaches. Framework services handle session persistence and automatic background extraction. Memory tools give the LLM explicit CRUD control over long-term memories. This is arguably the most powerful configuration, because the agent gets both automatic memory management and the ability to deliberately store or retrieve specific facts.

### Approach 3. MCP Tools (Model Context Protocol)

MCP is a standardized protocol for connecting agents to tools via Server-Sent Events (SSE). Instead of REST-based tool implementations, you point the agent at the Agent Memory Server's MCP endpoint and let ADK's `McpToolset` handle tool discovery automatically.

```python
from adk_redis.tools.mcp_memory import create_memory_mcp_toolset

memory_tools = create_memory_mcp_toolset(
    server_url="http://localhost:9000",
    tool_filter=["search_long_term_memory", "create_long_term_memories"],
)

agent = Agent(
    model="gemini-2.5-flash",
    name="fitness_coach",
    tools=[memory_tools],
)
```

The `tool_filter` parameter controls which MCP tools are exposed to the LLM. The Agent Memory Server exposes seven tools through MCP, including `search_long_term_memory`, `create_long_term_memories`, `get_long_term_memory`, `edit_long_term_memory`, `delete_long_term_memories`, `memory_prompt`, and `set_working_memory`.

The fitness coach example in the repo demonstrates this approach. It connects to memory via MCP and stores both semantic memories (user profile, injuries, equipment) and episodic memories (workouts with timestamps, milestones). The distinction between semantic and episodic memory types is particularly useful. Semantic memories represent timeless facts ("user has a knee injury"), while episodic memories represent events ("user completed 3x12 rows on March 9th").

MCP is the most standardized approach and makes it easy to swap memory backends without changing agent code. The tradeoff is that it requires running the Agent Memory Server with MCP support enabled on a separate port.

## Walking Through the Travel Agent

To make all of this concrete, let's trace through the `travel_agent_memory_hybrid` example, which is the most complete example in the repo. It combines framework-managed services, LLM-controlled memory tools, web search, itinerary planning, and calendar export into a single agent.

### The Entrypoint

The `main.py` file sets up the infrastructure. It registers custom service factories with ADK's service registry, creates both the session service and memory service, and launches a FastAPI app with the ADK web runner.

```python
from adk_redis.memory import RedisLongTermMemoryService, RedisLongTermMemoryServiceConfig
from adk_redis.sessions import RedisWorkingMemorySessionService, RedisWorkingMemorySessionServiceConfig

# Register factories so ADK can instantiate them from URIs
registry = get_service_registry()
registry.register_session_service("redis-working-memory", redis_session_factory)
registry.register_memory_service("redis-long-term-memory", redis_memory_factory)

# Build URIs and create the FastAPI app
app = get_fast_api_app(
    agents_dir=".",
    session_service_uri="redis-working-memory://localhost:8088",
    memory_service_uri="redis-long-term-memory://localhost:8088",
    web=True,
)
```

The URI-based factory pattern is worth noting. ADK's service registry lets you register custom service implementations behind URI schemes. This means you can switch between in-memory and Redis-backed services by changing a URI string, without modifying any agent code.

### The Agent

The agent itself is defined in `agent.py`. It assembles a rich set of tools spanning memory, search, and planning.

```python
from adk_redis.tools.memory import (
    SearchMemoryTool, CreateMemoryTool,
    UpdateMemoryTool, DeleteMemoryTool,
    MemoryToolConfig,
)
from google.adk.tools import preload_memory, load_memory

memory_config = MemoryToolConfig(
    api_base_url="http://localhost:8088",
    default_namespace="travel_agent_memory_hybrid",
    recency_boost=True,
    search_top_k=10,
)

tools = [
    SearchMemoryTool(config=memory_config),
    CreateMemoryTool(config=memory_config),
    UpdateMemoryTool(config=memory_config),
    DeleteMemoryTool(config=memory_config),
    preload_memory,
    load_memory,
    CalendarExportTool(),
    ItineraryPlannerTool(),
]
```

Notice the layered memory strategy. `preload_memory` and `load_memory` are ADK's built-in tools that hook into the `RedisLongTermMemoryService` we configured in `main.py`. These provide automatic, framework-controlled memory retrieval. The `SearchMemoryTool`, `CreateMemoryTool`, and friends give the LLM explicit control on top of that.

The agent also has an `after_agent_callback` that calls `add_session_to_memory()` after each turn. This is what triggers background extraction of facts and preferences into long-term memory.

```python
async def after_agent(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()

root_agent = Agent(
    model="gemini-2.5-flash",
    name="travel_agent",
    tools=tools,
    after_agent_callback=after_agent,
    instruction="...",  # Detailed prompt with memory management strategy
)
```

### What Happens at Runtime

When a user starts a conversation, the following sequence plays out.

1. ADK creates (or retrieves) a session via `RedisWorkingMemorySessionService`. The session is stored in the Agent Memory Server.
2. The agent's `preload_memory` tool automatically searches long-term memory for context relevant to the current conversation.
3. The user sends a message. The message is appended to working memory via the incremental append API.
4. The LLM generates a response. If it needs travel information, it can call web search tools. If it wants to check the user's preferences, it calls `SearchMemoryTool`. If the user shares a new preference, the LLM calls `CreateMemoryTool`.
5. The response is appended to working memory.
6. The `after_agent_callback` fires, sending the conversation to the Agent Memory Server for background extraction. The server pulls out facts like "user prefers direct flights" or "user wants to visit Japan in spring" and stores them as searchable long-term memories.
7. If the conversation grows long, the working memory service automatically summarizes older turns to stay within the context window.

All of this happens with a `pip install adk-redis[memory]`, a running Redis instance, and a running Agent Memory Server. The agent's Python code is clean, focused on domain logic rather than infrastructure plumbing.

## Getting Started

To run any of the examples, you need two things running.

**Redis 8.4** provides the storage backend for everything. Vector indices, session data, cache entries.

```bash
docker run -d --name redis -p 6379:6379 redis:8.4-alpine
```

**Redis Agent Memory Server** handles memory extraction, summarization, and the working memory API. It sits between your agent and Redis, adding the intelligence layer.

```bash
docker run -d --name agent-memory-server -p 8088:8088 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e GEMINI_API_KEY=your-key \
  -e GENERATION_MODEL=gemini/gemini-2.0-flash \
  -e EMBEDDING_MODEL=gemini/text-embedding-004 \
  redislabs/agent-memory-server:0.13.2 \
  agent-memory api --host 0.0.0.0 --port 8088 --task-backend=asyncio
```

The Agent Memory Server uses LiteLLM under the hood, which means it supports 100+ LLM providers. You can swap in OpenAI, Anthropic, AWS Bedrock, or even local models via Ollama.

Then install the package and run an example.

```bash
pip install adk-redis[all]
cd examples/simple_redis_memory
python main.py
```

## Conclusion

`adk-redis` is a focused library that solves a specific problem well. It takes the interfaces that ADK defines, `BaseMemoryService`, `BaseSessionService`, the tool system, the callback system, and provides Redis-backed implementations that are production-grade rather than toy-grade.

The key ideas worth taking away from this are the following.

The **two-tier memory architecture** (working memory for sessions, long-term memory for persistent facts) is a pattern that scales well. It mirrors how real applications need to manage state, keeping the current context fast and small while maintaining a durable knowledge base.

The **three integration approaches** (framework services, REST tools, MCP tools) give you a spectrum from fully automatic to fully LLM-controlled memory management. The hybrid approach, combining framework services with LLM-controlled tools, is particularly effective.

**Semantic caching** is a straightforward way to reduce costs and latency, and `adk-redis` makes it easy to enable without changing your agent's core logic.

The **search tools** provide a clean abstraction over RedisVL's query types, making it simple to add RAG capabilities to any ADK agent.

All of this runs on Redis, a system that most teams already know how to operate, monitor, and scale.

If you want to dive deeper, the [GitHub repository](https://github.com/redis-developer/adk-redis) has seven complete examples covering every feature described here. The [Redis Agent Memory Server documentation](https://github.com/redis/agent-memory-server) covers the memory backend in detail, and the [RedisVL documentation](https://docs.redisvl.com) covers the vector search and caching capabilities that power the tools and cache providers.