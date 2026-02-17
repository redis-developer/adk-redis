"""
Itinerary Planning Tool for Travel Agent

This tool helps structure multi-day travel itineraries with activities,
meals, and logistics organized by day and time.
"""

from typing import Any

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types


class ItineraryPlannerTool(BaseTool):
  """
  Tool for creating structured multi-day travel itineraries.

  Organizes activities, meals, and logistics into a day-by-day format
  that can be easily exported to calendar or shared with users.
  """

  def __init__(self, **kwargs: Any):
    super().__init__(
        name="plan_itinerary",
        description=(
            "Create a structured multi-day travel itinerary. "
            "Organizes activities, meals, transportation, and accommodations "
            "by day and time. Returns a formatted itinerary that can be "
            "exported to calendar or shared with the user. "
            "Use this when planning trips with multiple days or activities."
        ),
        **kwargs,
    )

  def _get_declaration(self) -> types.FunctionDeclaration:
    """Get the function declaration for the LLM."""
    return types.FunctionDeclaration(
        name=self.name,
        description=self.description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "destination": types.Schema(
                    type=types.Type.STRING,
                    description="Trip destination (e.g., 'Paris, France')",
                ),
                "start_date": types.Schema(
                    type=types.Type.STRING,
                    description="Trip start date (ISO format: YYYY-MM-DD)",
                ),
                "end_date": types.Schema(
                    type=types.Type.STRING,
                    description="Trip end date (ISO format: YYYY-MM-DD)",
                ),
                "days": types.Schema(
                    type=types.Type.ARRAY,
                    description="List of daily plans",
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "day_number": types.Schema(
                                type=types.Type.INTEGER,
                                description="Day number (1, 2, 3, etc.)",
                            ),
                            "date": types.Schema(
                                type=types.Type.STRING,
                                description="Date (YYYY-MM-DD)",
                            ),
                            "activities": types.Schema(
                                type=types.Type.ARRAY,
                                description="List of activities for this day",
                                items=types.Schema(
                                    type=types.Type.OBJECT,
                                    properties={
                                        "time": types.Schema(
                                            type=types.Type.STRING,
                                            description="Time (HH:MM format)",
                                        ),
                                        "title": types.Schema(
                                            type=types.Type.STRING,
                                            description="Activity name",
                                        ),
                                        "description": types.Schema(
                                            type=types.Type.STRING,
                                            description="Activity details",
                                        ),
                                        "location": types.Schema(
                                            type=types.Type.STRING,
                                            description="Address or place name",
                                        ),
                                        "duration_minutes": types.Schema(
                                            type=types.Type.INTEGER,
                                            description="Duration in minutes",
                                        ),
                                        "category": types.Schema(
                                            type=types.Type.STRING,
                                            description="Category (sightseeing, dining, transport, etc.)",
                                        ),
                                    },
                                ),
                            ),
                        },
                    ),
                ),
            },
            required=["destination", "start_date", "end_date", "days"],
        ),
    )

  async def run_async(
      self, *, args: dict[str, Any], tool_context: ToolContext
  ) -> dict[str, Any]:
    """
    Create a structured itinerary.

    Args:
        args: Dictionary containing destination, start_date, end_date, days
        tool_context: The tool context (unused)

    Returns:
        dict with:
            - success: bool
            - itinerary: structured itinerary data
            - summary: human-readable summary
            - calendar_events: list ready for export_to_calendar tool
    """
    destination = args.get("destination", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")
    days = args.get("days", [])

    # Validate inputs
    if not destination or not start_date or not end_date:
      return {
          "success": False,
          "error": "Missing required fields: destination, start_date, end_date",
      }

    if not days or len(days) == 0:
      return {
          "success": False,
          "error": "At least one day of activities is required",
      }

    # Build structured itinerary
    itinerary = {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": len(days),
        "days": [],
    }

    calendar_events = []
    summary_lines = [
        f"# {destination} Itinerary",
        f"📅 {start_date} to {end_date} ({len(days)} days)\n",
    ]

    for day in sorted(days, key=lambda d: d.get("day_number", 0)):
      day_number = day.get("day_number", 0)
      date = day.get("date", "")
      activities = day.get("activities", [])

      # Add to structured itinerary
      day_data = {
          "day_number": day_number,
          "date": date,
          "activities": activities,
          "activity_count": len(activities),
      }
      itinerary["days"].append(day_data)

      # Add to summary
      summary_lines.append(f"## Day {day_number} - {date}")

      # Process activities
      for activity in sorted(activities, key=lambda a: a.get("time", "00:00")):
        time = activity.get("time", "")
        title = activity.get("title", "Untitled Activity")
        description = activity.get("description", "")
        location = activity.get("location", "")
        duration = activity.get("duration_minutes", 60)
        category = activity.get("category", "activity")

        # Add to summary
        emoji = self._get_category_emoji(category)
        summary_lines.append(f"  {emoji} **{time}** - {title}")
        if location:
          summary_lines.append(f"      📍 {location}")
        if description:
          summary_lines.append(f"      {description}")

        # Create calendar event
        start_datetime = f"{date}T{time}:00"
        # Calculate end time (add duration)
        hour, minute = map(int, time.split(":"))
        end_minutes = hour * 60 + minute + duration
        end_hour = (end_minutes // 60) % 24
        end_minute = end_minutes % 60
        end_time = f"{end_hour:02d}:{end_minute:02d}"
        end_datetime = f"{date}T{end_time}:00"

        calendar_events.append(
            {
                "title": title,
                "start_date": start_datetime,
                "end_date": end_datetime,
                "location": location,
                "description": f"{category.title()}: {description}",
            }
        )

      summary_lines.append("")  # Blank line between days

    return {
        "success": True,
        "itinerary": itinerary,
        "summary": "\n".join(summary_lines),
        "calendar_events": calendar_events,
        "total_activities": sum(len(d.get("activities", [])) for d in days),
    }

  def _get_category_emoji(self, category: str) -> str:
    """Get emoji for activity category."""
    emoji_map = {
        "sightseeing": "🏛️",
        "dining": "🍽️",
        "breakfast": "🥐",
        "lunch": "🥗",
        "dinner": "🍷",
        "transport": "🚗",
        "flight": "✈️",
        "hotel": "🏨",
        "activity": "🎯",
        "shopping": "🛍️",
        "entertainment": "🎭",
        "relaxation": "🧘",
        "nature": "🌳",
    }
    return emoji_map.get(category.lower(), "📌")
