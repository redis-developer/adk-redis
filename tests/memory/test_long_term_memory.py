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

"""Tests for RedisLongTermMemoryService."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from adk_redis.memory import RedisLongTermMemoryService
from adk_redis.memory import RedisLongTermMemoryServiceConfig


class TestRedisLongTermMemoryServiceConfig:
  """Tests for RedisLongTermMemoryServiceConfig."""

  def test_default_values(self):
    """Test default configuration values."""
    config = RedisLongTermMemoryServiceConfig()
    assert config.api_base_url == "http://localhost:8000"
    assert config.timeout == 30.0
    assert config.default_namespace is None
    assert config.recency_boost is True
    assert config.recency_weight == 0.2
    assert config.semantic_weight == 0.8
    assert config.extraction_strategy == "discrete"
    assert config.extraction_strategy_config == {}

  def test_custom_values(self):
    """Test custom configuration values."""
    config = RedisLongTermMemoryServiceConfig(
        api_base_url="http://custom:9000",
        timeout=60.0,
        default_namespace="test_ns",
        recency_weight=0.5,
        semantic_weight=0.5,
        extraction_strategy="summary",
        extraction_strategy_config={"max_length": 100},
    )
    assert config.api_base_url == "http://custom:9000"
    assert config.timeout == 60.0
    assert config.default_namespace == "test_ns"
    assert config.recency_weight == 0.5
    assert config.semantic_weight == 0.5
    assert config.extraction_strategy == "summary"
    assert config.extraction_strategy_config == {"max_length": 100}


class TestRedisLongTermMemoryServiceInit:
  """Tests for RedisLongTermMemoryService initialization."""

  def test_init_with_default_config(self):
    """Test initialization with default config."""
    service = RedisLongTermMemoryService()
    assert service._config.api_base_url == "http://localhost:8000"

  def test_init_with_custom_config(self):
    """Test initialization with custom config."""
    config = RedisLongTermMemoryServiceConfig(
        api_base_url="http://custom:9000",
    )
    service = RedisLongTermMemoryService(config=config)
    assert service._config.api_base_url == "http://custom:9000"


class TestRedisLongTermMemoryServiceMethods:
  """Tests for RedisLongTermMemoryService methods."""

  @pytest.fixture
  def service(self):
    """Create a service instance for testing."""
    return RedisLongTermMemoryService()

  @pytest.mark.asyncio
  async def test_search_memory_returns_empty_on_error(self, service):
    """Test search_memory returns empty response on error."""
    with patch.object(
        service,
        "_client",
        create=True,
        new_callable=lambda: MagicMock(
            search_long_term_memory=AsyncMock(
                side_effect=Exception("Test error")
            )
        ),
    ):
      result = await service.search_memory(
          app_name="test_app",
          user_id="test_user",
          query="test query",
      )
      assert result.memories == []

  @pytest.mark.asyncio
  async def test_close_cleans_up_client(self, service):
    """Test close method cleans up client."""
    mock_client = MagicMock()
    mock_client.close = AsyncMock()

    # Manually set the cached property
    service.__dict__["_client"] = mock_client

    await service.close()

    mock_client.close.assert_called_once()
    assert "_client" not in service.__dict__
