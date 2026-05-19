# Redis SQL Search Agent

This sample shows an ADK agent answering catalog questions by emitting
SQL `SELECT` statements through the new `RedisSQLSearchTool`. The tool
wraps `redisvl.query.SQLQuery` (and the optional `sql-redis` extra),
which translates SQL into `FT.SEARCH` / `FT.AGGREGATE` against a Redis
search index.

## What this sample shows

- Configuring a `RedisSQLSearchTool` against a bound RedisVL index.
- Letting the LLM build SQL queries (with `:name` parameter placeholders)
  to answer structured questions about a product catalog.
- Wiring the tool into ADK's `Agent` and running it under `adk web`.

## Prerequisites

1. **Redis 8.4** running locally (or Redis Cloud with the RediSearch
   module enabled). The repo root has `./scripts/start-redis.sh` if you
   want an automated start.
2. **A Gemini API key**. Get one at
   [aistudio.google.com](https://aistudio.google.com/app/apikey).

No embeddings are required for this example, so you don't need a
vectorizer or NLTK stopwords.

## Setup

### 1. Install dependencies

From the repository root:

```bash
uv pip install 'adk-redis[sql,examples]'
```

The `sql` extra pulls in `redisvl[sql-redis]>=0.18.2`, which provides the
SQL-to-Redis query translation.

### 2. Start Redis 8.4

```bash
docker run -d --name redis -p 6379:6379 redis:8.4
docker exec redis redis-cli ping   # -> PONG
```

### 3. Set your Gemini API key

Copy `.env.example` to `.env` and fill in `GOOGLE_API_KEY`.

### 4. Load the sample catalog

```bash
cd examples/redis_sql_search
python load_data.py
```

This builds the `adk_sql_catalog` index and loads ten products spanning
electronics, fitness, kitchen, and office categories.

### 5. Run the agent

```bash
adk web redis_sql_search_agent
```

ADK web opens at `http://127.0.0.1:8000`. Pick the
`redis_sql_search_agent` app from the dropdown.

## Try these prompts

- "What electronics cost less than 100 dollars?"
- "Show me kitchen items with a rating of 4.5 or higher."
- "Find office furniture from DeskWorks under 500 dollars."
- "Which products have fewer than 20 in stock?"
- "List BrewLab products sorted by rating."

You will see the agent emit SQL like:

```sql
SELECT title, brand, price
FROM adk_sql_catalog
WHERE category = 'electronics' AND price < :max_price
```

with `params={"max_price": 100}` flowing through the same tool call.

## How it works

`RedisSQLSearchTool` exposes a two-parameter `FunctionDeclaration` to the
LLM:

- `sql`: a SQL `SELECT` statement (required).
- `params`: an optional object whose keys substitute the `:name`
  placeholders inside the SQL.

The tool builds a `redisvl.query.SQLQuery` and runs it against the bound
index, returning matching rows as `{"status": "success", "count": N,
"results": [...]}`. Errors become `{"status": "error", "error": "..."}`,
so the agent can fall back rather than crash.

See `RedisSQLSearchTool` in
[`src/adk_redis/tools/search/sql.py`](../../src/adk_redis/tools/search/sql.py)
for the implementation, and `redisvl.query.SQLQuery` for the underlying
SQL dialect.

## Cleanup

```bash
docker stop redis && docker rm redis
```
