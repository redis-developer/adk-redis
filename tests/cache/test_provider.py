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

"""Tests for adk_redis.cache._provider."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch
import warnings

import pytest

pytest.importorskip("redisvl")

from adk_redis.cache._provider import RedisVLCacheProvider
from adk_redis.cache._provider import RedisVLCacheProviderConfig


class TestRedisVLCacheProviderImportPath:
  """Provider must use the canonical redisvl.extensions.cache.llm path.

  redisvl 0.16+ deprecated redisvl.extensions.llmcache. The provider
  must source SemanticCache from the new location so no DeprecationWarning
  is raised when callers construct it.
  """

  def test_construction_does_not_emit_deprecation_warning(
      self, mock_vectorizer
  ):
    """RedisVLCacheProvider construction must not trip DeprecationWarning."""
    config = RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379",
        name="test_cache",
        ttl=60,
    )

    with patch(
        "redisvl.extensions.cache.llm.SemanticCache"
    ) as mock_semantic_cache:
      mock_semantic_cache.return_value = MagicMock()
      with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    mock_semantic_cache.assert_called_once()

  def test_construction_passes_expected_kwargs(self, mock_vectorizer):
    """Config values flow through to SemanticCache."""
    config = RedisVLCacheProviderConfig(
        redis_url="redis://localhost:6379/0",
        name="my_cache",
        ttl=120,
        distance_threshold=0.2,
    )

    with patch(
        "redisvl.extensions.cache.llm.SemanticCache"
    ) as mock_semantic_cache:
      RedisVLCacheProvider(config, vectorizer=mock_vectorizer)

    _, kwargs = mock_semantic_cache.call_args
    assert kwargs["name"] == "my_cache"
    assert kwargs["redis_url"] == "redis://localhost:6379/0"
    assert kwargs["ttl"] == 120
    assert kwargs["distance_threshold"] == 0.2
    assert kwargs["vectorizer"] is mock_vectorizer
    assert kwargs["overwrite"] is True
