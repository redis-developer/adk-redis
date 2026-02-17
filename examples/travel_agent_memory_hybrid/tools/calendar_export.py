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

"""Calendar Export Tool for Travel Itineraries.

This tool generates ICS (iCalendar) format files that can be imported into
Google Calendar, Outlook, Apple Calendar, and other calendar applications.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from google import genai
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext


class CalendarExportTool(BaseTool):
  """Tool for exporting travel itineraries to ICS calendar format.

  Generates ICS files that can be imported into:
  - Google Calendar
  - Microsoft Outlook
  - Apple Calendar
  - Any calendar app supporting iCalendar format
  """

  def __init__(self, **kwargs: Any):
    """Initialize the calendar export tool.

    Args:
        **kwargs: Additional keyword arguments passed to BaseTool
    """
    super().__init__(
        name="export_to_calendar",
        description=(
            "Export a travel itinerary to ICS calendar format. "
            "Creates calendar events for flights, hotels, activities, and other travel plans. "
            "Returns ICS file content that can be imported into Google Calendar, Outlook, or Apple Calendar. "
            "Use this when the user asks to 'add to calendar', 'export itinerary', or 'create calendar events'."
        ),
        **kwargs,
    )

  def _get_declaration(self) -> genai.types.FunctionDeclaration:
    """Get the tool declaration for the LLM."""
    return genai.types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters=genai.types.Schema(
            type=genai.types.Type.OBJECT,
            properties={
                "events": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    description="List of calendar events to create",
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        properties={
                            "title": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Event title (e.g., 'Flight to Tokyo', 'Hotel Check-in')",
                            ),
                            "start_date": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Start date/time in ISO 8601 format (e.g., '2026-03-15T10:00:00')",
                            ),
                            "end_date": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="End date/time in ISO 8601 format (e.g., '2026-03-15T14:00:00')",
                            ),
                            "location": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Event location (e.g., 'Tokyo Narita Airport', 'Grand Hyatt Tokyo')",
                            ),
                            "description": genai.types.Schema(
                                type=genai.types.Type.STRING,
                                description="Event details and notes",
                            ),
                        },
                        required=["title", "start_date", "end_date"],
                    ),
                ),
            },
            required=["events"],
        ),
    )

  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> dict[str, Any]:
    """Generate ICS calendar file from travel events.

    Args:
        args: Dictionary containing 'events' list
        tool_context: The tool context (unused)

    Returns:
        Dictionary with success status and ICS file content
    """
    events = args.get("events", [])
    try:
      # Generate ICS content
      ics_content = self._generate_ics(events)

      return {
          "success": True,
          "ics_content": ics_content,
          "event_count": len(events),
          "instructions": (
              "Copy the ICS content below and save it as a .ics file, "
              "then import it into your calendar app:\n"
              "• Google Calendar: Settings → Import & Export → Import\n"
              "• Outlook: File → Open & Export → Import/Export\n"
              "• Apple Calendar: File → Import"
          ),
      }
    except Exception as e:
      return {
          "success": False,
          "error": f"Failed to generate calendar export: {str(e)}",
      }

  def _generate_ics(self, events: list[dict[str, str]]) -> str:
    """Generate ICS file content from events.

    Args:
        events: List of event dictionaries

    Returns:
        ICS file content as string
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ADK-Redis Travel Agent//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for event in events:
      lines.extend(self._generate_event(event))

    lines.append("END:VCALENDAR")

    return "\n".join(lines)

  def _generate_event(self, event: dict[str, str]) -> list[str]:
    """Generate ICS VEVENT block for a single event.

    Args:
        event: Event dictionary with title, start_date, end_date, location, description

    Returns:
        List of ICS lines for this event
    """
    # Generate unique ID for this event
    uid = str(uuid4())

    # Parse dates and convert to ICS format (YYYYMMDDTHHMMSS)
    start_dt = self._parse_datetime(event["start_date"])
    end_dt = self._parse_datetime(event["end_date"])

    # Current timestamp for DTSTAMP
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART:{start_dt}",
        f"DTEND:{end_dt}",
        f"SUMMARY:{self._escape_text(event['title'])}",
    ]

    # Add optional fields
    if event.get("location"):
      lines.append(f"LOCATION:{self._escape_text(event['location'])}")

    if event.get("description"):
      lines.append(f"DESCRIPTION:{self._escape_text(event['description'])}")

    lines.append("END:VEVENT")

    return lines

  def _parse_datetime(self, dt_string: str) -> str:
    """Parse ISO 8601 datetime string to ICS format.

    Args:
        dt_string: ISO 8601 datetime string (e.g., '2026-03-15T10:00:00')

    Returns:
        ICS formatted datetime (e.g., '20260315T100000')
    """
    # Try parsing with timezone info first
    for fmt in [
        "%Y-%m-%dT%H:%M:%S%z",  # With timezone
        "%Y-%m-%dT%H:%M:%S",  # Without timezone
        "%Y-%m-%d",  # Date only
    ]:
      try:
        dt = datetime.strptime(dt_string, fmt)
        return dt.strftime("%Y%m%dT%H%M%S")
      except ValueError:
        continue

    # Fallback: return as-is if parsing fails
    return dt_string.replace("-", "").replace(":", "")

  def _escape_text(self, text: str) -> str:
    """Escape special characters for ICS format.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for ICS format
    """
    # ICS requires escaping of special characters
    text = text.replace("\\", "\\\\")  # Backslash
    text = text.replace(";", "\\;")  # Semicolon
    text = text.replace(",", "\\,")  # Comma
    text = text.replace("\n", "\\n")  # Newline

    return text
