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

"""Tests for RedisWorkingMemorySessionService."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from adk_redis.sessions import RedisWorkingMemorySessionService
from adk_redis.sessions import RedisWorkingMemorySessionServiceConfig


class TestRedisWorkingMemorySessionServiceConfig:
  """Tests for RedisWorkingMemorySessionServiceConfig."""

  def test_default_values(self):
    """Test default configuration values."""
    config = RedisWorkingMemorySessionServiceConfig()
    assert config.api_base_url == "http://localhost:8000"
    assert config.timeout == 30.0
    assert config.default_namespace is None
    assert config.model_name is None
    assert config.context_window_max is None
    assert config.extraction_strategy == "discrete"
    assert config.extraction_strategy_config == {}
    assert config.session_ttl_seconds is None

  def test_custom_values(self):
    """Test custom configuration values."""
    config = RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://custom:9000",
        timeout=60.0,
        default_namespace="test_ns",
        model_name="gpt-4",
        context_window_max=8000,
        extraction_strategy="summary",
        session_ttl_seconds=3600,
    )
    assert config.api_base_url == "http://custom:9000"
    assert config.timeout == 60.0
    assert config.default_namespace == "test_ns"
    assert config.model_name == "gpt-4"
    assert config.context_window_max == 8000
    assert config.extraction_strategy == "summary"
    assert config.session_ttl_seconds == 3600


class TestRedisWorkingMemorySessionServiceInit:
  """Tests for RedisWorkingMemorySessionService initialization."""

  def test_init_with_default_config(self):
    """Test initialization with default config."""
    service = RedisWorkingMemorySessionService()
    assert service._config.api_base_url == "http://localhost:8000"

  def test_init_with_custom_config(self):
    """Test initialization with custom config."""
    config = RedisWorkingMemorySessionServiceConfig(
        api_base_url="http://custom:9000",
    )
    service = RedisWorkingMemorySessionService(config=config)
    assert service._config.api_base_url == "http://custom:9000"


class TestRedisWorkingMemorySessionServiceMethods:
  """Tests for RedisWorkingMemorySessionService methods."""

  @pytest.fixture
  def service(self):
    """Create a service instance for testing."""
    return RedisWorkingMemorySessionService()

  @pytest.mark.asyncio
  async def test_list_sessions_returns_empty_on_error(self, service):
    """Test list_sessions returns empty list on error."""
    with patch.object(
        service,
        "_client",
        create=True,
        new_callable=lambda: MagicMock(
            list_sessions=AsyncMock(side_effect=Exception("Test error"))
        ),
    ):
      result = await service.list_sessions(
          app_name="test_app",
          user_id="test_user",
      )
      assert result.sessions == []

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
