# RedisVL MCP Search Agent

The **MCP-path mirror** of [`redis_search_tools/`](../redis_search_tools/).
Same knowledge-base corpus, same kinds of prompts, but search is served
by a separately-running `rvl mcp` server and the agent calls it via
ADK's standard `McpToolset` over MCP. No adk-redis wrapper involved;
this is the same pattern every MCP integration in the ADK catalog uses.

Use this example to compare the two deployment shapes side by side:

| | `redis_search_tools/` | `redisvl_mcp_search/` (this) |
|---|---|---|
| Topology | One process: agent + index in-process | Two processes: agent connects to `rvl mcp` over MCP |
| Tool count | 3 (semantic / keyword / range) | 1 (`search-records`, configured for hybrid) |
| Search modes covered | vector, BM25, range | vector + BM25 fused via FT.HYBRID |
| Where the vectorizer runs | In the agent process | In the `rvl mcp` server process |
| Filter shape | Python `FilterExpression` | JSON filter object parsed server-side |
| Use when | Single agent, fast onboarding, complex filters | Multi-agent / polyglot, server-side ops gates |

## What this sample shows

- Configuring `rvl mcp` for hybrid search via a YAML config.
- Connecting ADK to that server with ADK's native `McpToolset` + one of
  `StdioConnectionParams` / `StreamableHTTPConnectionParams`.
- Using a `tool_filter` to expose only `search-records` (no upserts).
- Reading the schema-aware tool description that RedisVL produces.

## Prerequisites

1. **Redis 8.4** running locally (or Redis Cloud with the RediSearch
   module enabled). Native `FT.HYBRID` requires 8.4+.
2. **A Gemini API key**. Get one at
   [aistudio.google.com](https://aistudio.google.com/app/apikey).
3. **`redisvl[mcp]>=0.18.2`** for the `rvl mcp` CLI, plus
   `sentence-transformers` (the loader and the MCP server both embed
   docs / queries with a HuggingFace vectorizer).

## Setup

### 1. Install dependencies

From the repository root:

```bash
uv pip install 'adk-redis[examples]' 'redisvl[mcp]>=0.18.2' sentence-transformers
```

### 2. Start Redis 8.4

```bash
docker run -d --name redis -p 6379:6379 redis:8.4
docker exec redis redis-cli ping   # -> PONG
```

### 3. Set your Gemini API key

Copy `.env.example` to `.env` and fill in `GOOGLE_API_KEY`. Optional:

- `REDIS_URL` to point the loader at a non-default Redis.
- `REDISVL_MCP_URL` if you run the MCP server somewhere other than
  `http://127.0.0.1:8765/mcp`.
- `REDISVL_MCP_AUTH_TOKEN` to attach a bearer token to MCP requests.

### 4. Load the knowledge base

```bash
cd examples/redisvl_mcp_search
python load_data.py
```

The loader creates the `adk_mcp_knowledge_base` index, embeds the
documents with `redis/langcache-embed-v2` (768 dims), and writes them
to Redis with stable keys so re-running is idempotent.

### 5. Start the RedisVL MCP server

In a separate terminal:

```bash
cd examples/redisvl_mcp_search
rvl mcp --config mcp_config.yaml \
  --transport streamable-http \
  --host 127.0.0.1 --port 8765
```

The server inspects the configured index, registers a single hybrid
`search-records` tool with schema-aware filter and return-field hints,
and listens on `http://127.0.0.1:8765/mcp`.

### 6. Run the agent

```bash
adk web redisvl_mcp_search_agent
```

ADK web opens at `http://127.0.0.1:8000`. Pick the
`redisvl_mcp_search_agent` app from the dropdown.

## Example queries

Mirror the prompts from `redis_search_tools/` so you can see the MCP path
return analogous results:

- **Semantic-leaning:** "What is Redis?", "How does RAG work?", "What is
  a vector database?"
- **Keyword-leaning:** "Tell me about HNSW.", "Explain BM25 scoring.",
  "FT.HYBRID command."
- **Mixed:** "What are RAG best practices?", "How do I build an
  intelligent assistant?"

Because the server is configured for hybrid mode, a single query
exercises both the BM25 path (term matches in `content`) and the vector
path (semantic similarity to the query embedding), then fuses with
`LINEAR` weighting (50% text, 50% vector by default).

## Files

| File | Purpose |
|------|---------|
| `schema.yaml` | RedisVL index schema (text + tag + vector fields). |
| `load_data.py` | Embeds and loads the knowledge-base corpus. |
| `mcp_config.yaml` | `rvl mcp` server configuration: hybrid search + vectorizer + runtime field names. |
| `redisvl_mcp_search_agent/agent.py` | The ADK agent. |
| `.env.example` | Template for `GOOGLE_API_KEY` and optional overrides. |

## How it works

1. **Agent constructs an MCP toolset.** ADK's `McpToolset` is wired to
   the running `rvl mcp` server with either `StdioConnectionParams`
   (default in this example, spawns `rvl mcp --config <path>`) or
   `StreamableHTTPConnectionParams` (`REDISVL_MCP_URL` env var).
   `tool_filter=["search-records"]` hides `upsert-records` so the agent
   cannot write.
2. **Agent emits a query.** The LLM calls `search-records({"query":
   "...", "limit": 5})`. ADK relays the call to the MCP server.
3. **MCP server runs hybrid search.** The server embeds the query with
   `redis/langcache-embed-v2`, builds a `HybridQuery` against the
   configured index, runs `FT.HYBRID` on Redis, normalizes scores, and
   returns structured results with `{title, content, url, ...}` per
   match.
4. **Agent summarizes.** The LLM cites each match's title and url.

## Customization

### Switch fusion method

Edit `mcp_config.yaml`:

```yaml
search:
  type: hybrid
  params:
    combination_method: RRF
    rrf_window: 20
    rrf_constant: 60
```

### Add a bearer token

Run the server behind a proxy that injects auth, then set
`REDISVL_MCP_URL` and `REDISVL_MCP_AUTH_TOKEN`. The example agent reads
both and attaches `Authorization: Bearer <token>` to every MCP request
via `StreamableHTTPConnectionParams(headers=...)`.

### Connect to Redis Cloud

Set `REDIS_URL` before running both the loader and the MCP server. The
config YAML uses `${REDIS_URL:-redis://localhost:6379}` so the override
flows through automatically.

## Cleanup

```bash
docker stop redis && docker rm redis
```

## See also

- [`redis_search_tools/`](../redis_search_tools/) for the in-process
  Python version of the same demo.
- [`redis_sql_search/`](../redis_sql_search/) for SQL-style filters
  (in-process only; no MCP equivalent today).
- [Search tools how-to](../../docs/user_guide/how_to_guides/search_tools.md)
  for the full decision matrix.
