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

"""Utility functions for memory services."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import hashlib
from typing import Any, TYPE_CHECKING

from google.genai import types

if TYPE_CHECKING:
  from google.adk.events.event import Event


def extract_text_from_event(event: "Event") -> str:
  """Extracts text content from an event's content parts.

  Filters out thought parts and only extracts actual text content.
  This ensures metadata like thoughtSignature is not stored in memories.

  Args:
      event: The event to extract text from.

  Returns:
      Combined text from all text parts (excluding thoughts), or empty string if none found.
  """
  if not event.content or not event.content.parts:
    return ""

  # Filter out thought parts and only extract text
  # This prevents metadata like thoughtSignature from being stored
  text_parts = [
      part.text
      for part in event.content.parts
      if part.text and not part.thought
  ]
  return " ".join(text_parts)


def extract_text_from_content(content: types.Content | None) -> str:
  """Extract text content from a GenAI content object.

  Args:
      content: Content object to read.

  Returns:
      Combined non-empty text parts.
  """
  if not content or not content.parts:
    return ""

  text_parts = [
      part.text.strip()
      for part in content.parts
      if part.text and part.text.strip()
  ]
  return "\n".join(text_parts)


def timestamp_to_datetime(timestamp: float) -> datetime:
  """Convert a Unix timestamp to a UTC datetime.

  Args:
      timestamp: Unix timestamp in seconds.

  Returns:
      Timezone-aware UTC datetime.
  """
  return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def stable_memory_id(*parts: object) -> str:
  """Build a deterministic memory ID from stable input parts.

  Args:
      *parts: Values that uniquely identify the memory.

  Returns:
      A deterministic Redis Agent Memory ID.
  """
  digest = hashlib.sha256(
      ":".join(str(part) for part in parts).encode("utf-8")
  ).hexdigest()
  return f"adk-{digest[:32]}"


def read_field(value: object, name: str, default: Any = None) -> Any:
  """Read a field from either a dict or an object.

  Args:
      value: Mapping or object to inspect.
      name: Field or attribute name.
      default: Value returned when the field is absent.

  Returns:
      Field value or default.
  """
  if isinstance(value, dict):
    return value.get(name, default)
  return getattr(value, name, default)


def is_not_found_error(exc: Exception) -> bool:
  """Return True when a Redis Agent Memory exception represents a 404.

  Args:
      exc: Exception raised by the Redis Agent Memory SDK.

  Returns:
      True when the SDK reported a missing resource.
  """
  return (
      getattr(exc, "status_code", None) == 404
      or exc.__class__.__name__ == "NotFoundErrorResponseContent"
  )
