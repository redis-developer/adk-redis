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

"""Tests for version information."""


def test_version_exists():
    """Test that version is defined."""
    from adk_redis import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)


def test_version_format():
    """Test that version follows semver format."""
    from adk_redis import __version__

    parts = __version__.split(".")
    assert len(parts) >= 2
    # First two parts should be numeric
    assert parts[0].isdigit()
    assert parts[1].isdigit()
