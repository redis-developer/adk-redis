# Copyright 2025 Google LLC
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

    def get_function_declaration(self) -> genai.types.FunctionDeclaration:
        """Define the tool's function signature for the LLM."""
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

    async def run(self, events: list[dict[str, str]]) -> dict[str, Any]:
        """Generate ICS calendar file from travel events.
        
        Args:
            events: List of event dictionaries with title, start_date, end_date, location, description
            
        Returns:
            Dictionary with success status and ICS file content
        """
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

