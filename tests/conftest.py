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

"""Pytest configuration and fixtures for adk-redis tests."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_vectorizer():
  """Mock RedisVL vectorizer."""
  try:
    from redisvl.utils.vectorize import BaseVectorizer

    vectorizer = MagicMock(spec=BaseVectorizer)
  except ImportError:
    vectorizer = MagicMock()

  vectorizer.embed = MagicMock(return_value=[0.1] * 384)
  vectorizer.aembed = AsyncMock(return_value=[0.1] * 384)
  return vectorizer


@pytest.fixture
def mock_search_index():
  """Mock RedisVL SearchIndex."""
  try:
    from redisvl.index import SearchIndex

    index = MagicMock(spec=SearchIndex)
  except ImportError:
    index = MagicMock()

  index.query = MagicMock(
      return_value=[
          {
              "title": "Test Doc",
              "content": "Test content",
              "vector_distance": 0.1,
          }
      ]
  )
  return index


@pytest.fixture
def mock_async_search_index():
  """Mock RedisVL AsyncSearchIndex."""
  try:
    from redisvl.index import AsyncSearchIndex

    index = MagicMock(spec=AsyncSearchIndex)
  except ImportError:
    index = MagicMock()

  index.query = AsyncMock(
      return_value=[
          {
              "title": "Test Doc",
              "content": "Test content",
              "vector_distance": 0.1,
          }
      ]
  )
  return index


@pytest.fixture
def mock_memory_client():
  """Mock MemoryAPIClient for memory service tests."""
  client = MagicMock()
  client.search_long_term_memory = AsyncMock(
      return_value=MagicMock(memories=[])
  )
  client.create_long_term_memories = AsyncMock(return_value=None)
  client.close = AsyncMock()
  return client


@pytest.fixture
def mock_session_client():
  """Mock MemoryAPIClient for session service tests."""
  client = MagicMock()
  client.get_or_create_working_memory = AsyncMock(
      return_value=(
          True,
          MagicMock(messages=[], data={}, session_id="test-session"),
      )
  )
  client.put_working_memory = AsyncMock()
  client.delete_working_memory = AsyncMock()
  client.list_sessions = AsyncMock(return_value=MagicMock(sessions=[]))
  client.append_messages_to_working_memory = AsyncMock()
  client.close = AsyncMock()
  return client
