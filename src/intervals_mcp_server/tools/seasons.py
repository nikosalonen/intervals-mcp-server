"""
Season management MCP tools for Intervals.icu.

Seasons are events with category=SEASON_START that partition the training
timeline into phases (e.g. "Base", "Build", "Peak").
"""

import logging
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.mcp_instance import mcp
from intervals_mcp_server.utils.dates import get_default_start_date, get_default_future_end_date
from intervals_mcp_server.utils.formatting import format_season_summary
from intervals_mcp_server.utils.schemas import EventResponse
from intervals_mcp_server.utils.validation import resolve_athlete_id

logger = logging.getLogger(__name__)
config = get_config()


@mcp.tool()
async def list_seasons(
    athlete_id: str | None = None,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """List training seasons for an athlete from Intervals.icu.

    Seasons are SEASON_START events that partition the training timeline into
    phases (e.g. "Base", "Build", "Peak").

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 1 year ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to 1 year from now)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    if not start_date:
        start_date = get_default_start_date(days_ago=365)
    if not end_date:
        end_date = get_default_future_end_date(days_ahead=365)

    params = {"oldest": start_date, "newest": end_date, "category": "SEASON_START"}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/events", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching seasons: {result.get('message', 'Unknown error')}"

    if not result:
        return f"No seasons found for athlete {athlete_id_to_use} in the specified date range."

    events = result if isinstance(result, list) else []
    if not events:
        return f"No seasons found for athlete {athlete_id_to_use} in the specified date range."

    formatted: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            formatted.append(format_season_summary(EventResponse.from_dict(event)))
        except (TypeError, KeyError, ValueError) as e:
            eid = event.get("id", "unknown")
            logger.error("Failed to format season %s: %s", eid, e, exc_info=True)
            formatted.append(f"[Season {eid}: failed to format]")

    if not formatted:
        return f"No seasons found for athlete {athlete_id_to_use} in the specified date range."

    return "Seasons:\n\n" + "\n\n".join(formatted)


@mcp.tool()
async def create_season(
    name: str,
    start_date: str,
    athlete_id: str | None = None,
    api_key: str | None = None,
    end_date: str | None = None,
    description: str | None = None,
    color: str | None = None,
) -> str:
    """Create a new training season on the athlete's calendar.

    A season is a SEASON_START event that marks the beginning of a training phase.

    Args:
        name: Name of the season (e.g. "Base", "Build", "Peak", "Race")
        start_date: Start date in YYYY-MM-DD format
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        end_date: End date in YYYY-MM-DD format (optional)
        description: Season description (optional)
        color: Color hex code, e.g. "#FF5733" (optional)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    event_data: dict[str, Any] = {
        "start_date_local": start_date + "T00:00:00",
        "category": "SEASON_START",
        "name": name,
    }
    if end_date is not None:
        event_data["end_date_local"] = end_date + "T00:00:00"
    if description is not None:
        event_data["description"] = description
    if color is not None:
        event_data["color"] = color

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/events",
        api_key=api_key,
        method="POST",
        data=event_data,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error creating season: {result.get('message', 'Unknown error')}"

    if not isinstance(result, dict):
        return "Error creating season: unexpected response."

    try:
        return "Season created successfully:\n\n" + format_season_summary(
            EventResponse.from_dict(result)
        )
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to format created season: %s", e, exc_info=True)
        return "Season created but failed to format response."


@mcp.tool()
async def update_season(
    event_id: str,
    athlete_id: str | None = None,
    api_key: str | None = None,
    name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    description: str | None = None,
    color: str | None = None,
) -> str:
    """Update an existing training season.

    Args:
        event_id: The Intervals.icu event ID of the season to update
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        name: New name for the season (optional)
        start_date: New start date in YYYY-MM-DD format (optional)
        end_date: New end date in YYYY-MM-DD format (optional)
        description: New description (optional)
        color: New color hex code, e.g. "#FF5733" (optional)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    event_data: dict[str, Any] = {"category": "SEASON_START"}
    if name is not None:
        event_data["name"] = name
    if start_date is not None:
        event_data["start_date_local"] = start_date + "T00:00:00"
    if end_date is not None:
        event_data["end_date_local"] = end_date + "T00:00:00"
    if description is not None:
        event_data["description"] = description
    if color is not None:
        event_data["color"] = color

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/events/{event_id}",
        api_key=api_key,
        method="PUT",
        data=event_data,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error updating season: {result.get('message', 'Unknown error')}"

    if not isinstance(result, dict):
        return "Error updating season: unexpected response."

    try:
        return "Season updated successfully:\n\n" + format_season_summary(
            EventResponse.from_dict(result)
        )
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to format updated season: %s", e, exc_info=True)
        return "Season updated but failed to format response."
