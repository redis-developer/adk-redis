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

"""Load sample product catalog into Redis for the redis_sql_search demo.

The catalog is small but deliberately mixed so SQL filters demonstrate
real differentiation:

- range filters (`price < 100`, `rating >= 4.5`)
- tag equality (`category = 'electronics'`)
- text matching against the description
- combined predicates and parameterized queries
"""

import os
from pathlib import Path

from redisvl.index import SearchIndex

SAMPLE_PRODUCTS = [
    {
        "title": "Wireless Headphones",
        "description": "Over-ear bluetooth headphones with active noise cancellation.",
        "category": "electronics",
        "brand": "Acoustica",
        "price": 199,
        "rating": 4.6,
        "stock": 42,
    },
    {
        "title": "Wired Earbuds",
        "description": "Affordable wired earbuds with an inline microphone.",
        "category": "electronics",
        "brand": "SoundLite",
        "price": 25,
        "rating": 4.1,
        "stock": 250,
    },
    {
        "title": "Smart Coffee Maker",
        "description": "App-controlled drip coffee maker with grinder and warm plate.",
        "category": "kitchen",
        "brand": "BrewLab",
        "price": 149,
        "rating": 4.3,
        "stock": 15,
    },
    {
        "title": "Espresso Machine",
        "description": "Semi-automatic espresso machine with 15 bar pump.",
        "category": "kitchen",
        "brand": "BrewLab",
        "price": 549,
        "rating": 4.8,
        "stock": 6,
    },
    {
        "title": "Yoga Mat",
        "description": "Non-slip 6mm thick yoga mat with carrying strap.",
        "category": "fitness",
        "brand": "ZenFlow",
        "price": 35,
        "rating": 4.7,
        "stock": 120,
    },
    {
        "title": "Adjustable Dumbbells",
        "description": "Pair of adjustable dumbbells, 5 to 50 pounds per side.",
        "category": "fitness",
        "brand": "ZenFlow",
        "price": 299,
        "rating": 4.5,
        "stock": 18,
    },
    {
        "title": "Standing Desk",
        "description": "Electric sit-stand desk with memory presets.",
        "category": "office",
        "brand": "DeskWorks",
        "price": 499,
        "rating": 4.4,
        "stock": 9,
    },
    {
        "title": "Ergonomic Chair",
        "description": "Mesh-back ergonomic office chair with adjustable lumbar.",
        "category": "office",
        "brand": "DeskWorks",
        "price": 329,
        "rating": 4.2,
        "stock": 30,
    },
    {
        "title": "Mechanical Keyboard",
        "description": "Tenkeyless mechanical keyboard with tactile switches.",
        "category": "electronics",
        "brand": "SoundLite",
        "price": 89,
        "rating": 4.7,
        "stock": 55,
    },
    {
        "title": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI, ethernet, and SD reader.",
        "category": "electronics",
        "brand": "Acoustica",
        "price": 49,
        "rating": 4.0,
        "stock": 200,
    },
]


def load_data() -> None:
  """Load the sample product catalog into Redis."""
  schema_path = Path(__file__).parent / "schema.yaml"
  redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

  print(f"Connecting to Redis at {redis_url}")
  index = SearchIndex.from_yaml(str(schema_path))
  index.connect(redis_url)

  print("Creating index (will overwrite if exists)...")
  index.create(overwrite=True, drop=True)

  print(f"Loading {len(SAMPLE_PRODUCTS)} products into Redis...")
  # Stable keys so re-running the loader overwrites instead of duplicating.
  keys = [f"{index.prefix}:{i:04d}" for i in range(len(SAMPLE_PRODUCTS))]
  index.load(SAMPLE_PRODUCTS, keys=keys)

  print(
      """
Loaded products. The agent can now answer questions like:

  - "What electronics cost less than 100 dollars?"
  - "Show me kitchen items with a rating of 4.5 or higher."
  - "Find office furniture from DeskWorks under 500 dollars."
  - "Which products have fewer than 20 in stock?"

Run: adk web redis_sql_search_agent
"""
  )


if __name__ == "__main__":
  load_data()
