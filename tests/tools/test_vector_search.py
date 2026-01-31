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

"""Tests for RedisVectorSearchTool."""

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

# Skip all tests if redisvl is not installed
pytest.importorskip("redisvl")

from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.utils.vectorize import BaseVectorizer

from adk_redis import RedisVectorQueryConfig
from adk_redis import RedisVectorSearchTool


@pytest.fixture
def mock_vectorizer():
    """Mock RedisVL vectorizer."""
    vectorizer = MagicMock(spec=BaseVectorizer)
    vectorizer.embed = MagicMock(return_value=[0.1] * 384)
    vectorizer.aembed = AsyncMock(return_value=[0.1] * 384)
    return vectorizer


@pytest.fixture
def mock_index():
    """Mock RedisVL SearchIndex."""
    index = MagicMock(spec=SearchIndex)
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
def vector_search_tool(mock_index, mock_vectorizer):
    """Create RedisVectorSearchTool instance for testing."""
    config = RedisVectorQueryConfig(num_results=5)
    return RedisVectorSearchTool(
        index=mock_index,
        vectorizer=mock_vectorizer,
        config=config,
        return_fields=["title", "content"],
    )


class TestRedisVectorSearchToolInit:
    """Tests for RedisVectorSearchTool initialization."""

    def test_default_parameters(self, mock_index, mock_vectorizer):
        """Test default parameter values with default config."""
        tool = RedisVectorSearchTool(
            index=mock_index,
            vectorizer=mock_vectorizer,
        )
        # Config defaults
        assert tool._config.vector_field_name == "embedding"
        assert tool._config.num_results == 10
        assert tool._config.dtype == "float32"
        assert tool._config.return_score is True
        assert tool._config.dialect == 2
        assert tool._config.in_order is False
        assert tool._config.normalize_vector_distance is False
        assert tool._config.sort_by is None
        assert tool._config.hybrid_policy is None
        assert tool._config.batch_size is None
        assert tool._config.ef_runtime is None
        assert tool._config.epsilon is None
        # Tool-level defaults
        assert tool._filter_expression is None

    def test_custom_parameters_via_config(self, mock_index, mock_vectorizer):
        """Test custom parameter values via config object."""
        config = RedisVectorQueryConfig(
            vector_field_name="custom_embedding",
            num_results=20,
            dtype="float64",
            return_score=False,
            dialect=3,
            in_order=True,
            normalize_vector_distance=True,
            hybrid_policy="BATCHES",
            batch_size=100,
            ef_runtime=200,
            epsilon=0.01,
        )
        tool = RedisVectorSearchTool(
            index=mock_index,
            vectorizer=mock_vectorizer,
            config=config,
            return_fields=["title", "content", "url"],
        )
        assert tool._config.vector_field_name == "custom_embedding"
        assert tool._config.num_results == 20
        assert tool._return_fields == ["title", "content", "url"]
        assert tool._config.dtype == "float64"
        assert tool._config.return_score is False
        assert tool._config.dialect == 3
        assert tool._config.in_order is True
        assert tool._config.normalize_vector_distance is True
        assert tool._config.hybrid_policy == "BATCHES"
        assert tool._config.batch_size == 100
        assert tool._config.ef_runtime == 200
        assert tool._config.epsilon == 0.01

    def test_custom_name_and_description(self, mock_index, mock_vectorizer):
        """Test custom tool name and description."""
        tool = RedisVectorSearchTool(
            index=mock_index,
            vectorizer=mock_vectorizer,
            name="custom_search",
            description="Custom search description",
        )
        assert tool.name == "custom_search"
        assert tool.description == "Custom search description"


class TestRedisVectorSearchToolBuildQuery:
    """Tests for _build_query method."""

    def test_build_query_basic(self, vector_search_tool):
        """Test basic query building."""
        embedding = [0.1] * 384
        query = vector_search_tool._build_query("test query", embedding)

        assert isinstance(query, VectorQuery)
        # VectorQuery uses private attributes
        assert query._vector == embedding
        assert query._vector_field_name == "embedding"
        assert query._num_results == 5

    def test_build_query_with_num_results_override(self, vector_search_tool):
        """Test query building with num_results override."""
        embedding = [0.1] * 384
        query = vector_search_tool._build_query(
            "test query", embedding, num_results=15
        )

        assert query._num_results == 15
