# RedisVL MCP Search Agent

This sample shows an ADK agent that talks to a separately-running
**RedisVL MCP server** (`rvl mcp`) via the new
`create_redisvl_mcp_toolset(...)` helper. The MCP server is configured
to expose BM25 fulltext search over a small corpus of Redis articles.

## What this sample shows

- Configuring `rvl mcp` for a Redis search index with a YAML file.
- Connecting ADK to that server with `create_redisvl_mcp_toolset(...)`
  over the `streamable-http` transport.
- Using a `tool_filter` to expose only `search-records` (no upserts).
- Reading the schema-aware tool description that RedisVL produces.

## Architecture

```
                +-------------------+
   "search-     |  rvl mcp server   |
   records"     |  (streamable-http |
       ^^^^^^^^>|   on :8765)       |---->  Redis 8.4+ (RediSearch)
       MCP      +-------------------+
       protocol             ^
                            |
                +-------------------+
                | ADK agent         |
                | (`adk web`)       |
                | create_redisvl_   |
                | mcp_toolset(...)  |
                +-------------------+
```

## Prerequisites

1. **Redis 8.4** running locally or in Redis Cloud. The repo root has
   `./scripts/start-redis.sh` for a one-shot start.
2. **A Gemini API key**. Get one at
   [aistudio.google.com](https://aistudio.google.com/app/apikey).
3. **The `mcp-search` extra** so the helper and `rvl mcp` CLI are
   installed.

## Setup

### 1. Install dependencies

From the repository root:

```bash
uv pip install 'adk-redis[mcp-search,examples]'
```

The `mcp-search` extra pulls in `redisvl[mcp]>=0.18.2`, which provides
the `rvl mcp` CLI and the FastMCP server.

### 2. Start Redis 8.4

```bash
docker run -d --name redis -p 6379:6379 redis:8.4
docker exec redis redis-cli ping   # -> PONG
```

### 3. Set your Gemini API key

Copy `.env.example` to `.env` and fill in `GOOGLE_API_KEY`. Optionally
set `REDISVL_MCP_URL` if you plan to run the MCP server somewhere other
than `http://127.0.0.1:8765/mcp`.

### 4. Load the article index

```bash
cd examples/redisvl_mcp_search
python load_data.py
```

This creates the `adk_mcp_articles` index and loads six short articles
about Redis search, MCP, semantic caching, and agent memory.

### 5. Start the RedisVL MCP server

In a separate terminal:

```bash
cd examples/redisvl_mcp_search
rvl mcp --config mcp_config.yaml \
  --transport streamable-http \
  --host 127.0.0.1 --port 8765
```

The server inspects the configured index, registers its `search-records`
tool with schema-aware filter hints, and starts listening on
`http://127.0.0.1:8765/mcp`.

### 6. Run the agent

```bash
adk web redisvl_mcp_search_agent
```

ADK web opens at `http://127.0.0.1:8000`. Pick the
`redisvl_mcp_search_agent` app from the dropdown.

## Try these prompts

- "Find articles about FT.HYBRID."
- "What does the MCP server expose?"
- "Explain semantic caching."
- "Tell me about HNSW runtime parameters."

The agent decides on a keyword phrase, calls `search-records` over MCP,
and summarizes the matches with title and URL citations.

## How it works

`create_redisvl_mcp_toolset(...)` returns an ADK `McpToolset` with the
right connection-params type for the transport you choose:

- `transport="stdio"` (passes a `config_path`): spawns
  `rvl mcp --config <path> --read-only` over stdio.
- `transport="streamable-http"` (default, passes a `url`): connects to
  a long-running server. Bearer auth is added to headers when
  `auth_token` is set.
- `transport="sse"` (passes a `url`): same as streamable-http but over
  the SSE transport.

The agent in this sample uses the streamable-http path so the MCP server
can stay up between agent invocations. Switch to stdio if you prefer a
single process; the helper handles it.

## Cleanup

```bash
docker stop redis && docker rm redis
```
