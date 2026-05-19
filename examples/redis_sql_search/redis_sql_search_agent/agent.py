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

"""Redis SQL search agent.

Exposes a `RedisSQLSearchTool` over a small product catalog so the LLM can
issue SQL SELECT statements to answer natural-language questions about the
catalog. Demonstrates parameterized queries via `:name` placeholders.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk import Agent
from redisvl.index import SearchIndex

from adk_redis import RedisSQLSearchTool

SCHEMA_PATH = Path(__file__).parent.parent / "schema.yaml"
INDEX_NAME = "adk_sql_catalog"

INSTRUCTION = f"""You are a catalog assistant with access to a Redis search
index named `{INDEX_NAME}`. Each document represents a product.

You have one tool: `catalog_sql_search`. It runs SQL SELECT statements
against the index. Use the schema below when composing queries.

## Schema

Table (the index name): `{INDEX_NAME}`

Columns:

  - title (text)
  - description (text)
  - category (tag): electronics | fitness | kitchen | office
  - brand (tag): Acoustica | SoundLite | BrewLab | ZenFlow | DeskWorks
  - price (numeric)
  - rating (numeric)
  - stock (numeric)

## Query guidance

- Filter `category` and `brand` with `=`, e.g. `WHERE category = 'kitchen'`.
- Compare numeric columns with `<`, `<=`, `>`, `>=`, `=`, `BETWEEN`.
- For free-text matching on `title` / `description`, use `LIKE` with `%`
  wildcards or `fulltext(field, 'phrase')` for tokenized search.
- When the user supplies a numeric threshold, pass it via the `params`
  object using a `:name` placeholder in the SQL.

Example query the user might ask:
  "What electronics cost less than 100 dollars?"

Example tool call you should make:
  sql:    SELECT title, brand, price FROM {INDEX_NAME}
          WHERE category = 'electronics' AND price < :max_price
  params: {{"max_price": 100}}

After calling the tool, summarize the matching rows for the user. Cite
the title, brand, and price of each match. If the result is empty, say
so plainly; do not invent products.
"""


def get_index(schema_path: Path, redis_url: str) -> SearchIndex:
  """Load the schema and connect to Redis."""
  index = SearchIndex.from_yaml(str(schema_path))
  index.connect(redis_url)
  return index


def create_agent() -> Agent:
  """Create the SQL search agent."""
  load_dotenv()

  redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
  index = get_index(SCHEMA_PATH, redis_url)

  sql_tool = RedisSQLSearchTool(
      index=index,
      name="catalog_sql_search",
      description=(
          "Run a SQL SELECT statement against the Redis product catalog. "
          "Use :param placeholders and supply a matching params object."
      ),
  )

  return Agent(
      model="gemini-2.5-flash",
      name="redis_sql_search_agent",
      instruction=INSTRUCTION,
      tools=[sql_tool],
  )


root_agent = create_agent()


if __name__ == "__main__":
  print(f"Agent '{root_agent.name}' created with {len(root_agent.tools)} tools")
  for tool in root_agent.tools:
    print(f"  - {tool.name}")
