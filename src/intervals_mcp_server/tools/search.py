"""
Activity search MCP tools for Intervals.icu.

This module contains tools for searching activities by name/tag and by interval patterns.
"""

import logging

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_search_result
from intervals_mcp_server.utils.schemas import Activity
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

logger = logging.getLogger(__name__)
config = get_config()


@mcp.tool()
async def search_activities(
    athlete_id: str | None = None,
    q: str | None = None,
    limit: int | None = None,
    api_key: str | None = None,
) -> str:
    """Search activities by name or tag.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        q: Search query (name or tag).
        limit: Maximum number of results (optional).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    params: dict[str, str | int] = {}
    if q:
        params["q"] = q
    if limit is not None:
        params["limit"] = limit

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/search",
        api_key=api_key,
        params=params if params else None,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error searching activities: {result.get('message', 'Unknown error')}"

    activities = result if isinstance(result, list) else []
    formatted = [
        format_search_result(Activity.from_dict(a)) for a in activities if isinstance(a, dict)
    ]
    if not formatted:
        return "No activities found."

    return "Search results:\n\n" + "\n".join(formatted)


@mcp.tool()
async def search_intervals(
    athlete_id: str | None = None,
    duration_seconds: int | None = None,
    intensity_min: float | None = None,
    intensity_max: float | None = None,
    interval_type: str | None = None,
    reps: int | None = None,
    limit: int | None = None,
    api_key: str | None = None,
) -> str:
    """Find activities that contain intervals matching duration and intensity range.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        duration_seconds: Interval duration in seconds to match.
        intensity_min: Minimum intensity (e.g. 0.9 for 90% FTP).
        intensity_max: Maximum intensity.
        interval_type: Optional interval type filter (e.g. 'work', 'recovery').
        reps: Optional number of reps to match.
        limit: Maximum number of activities to return (optional).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    params: dict[str, str | int | float] = {}
    if duration_seconds is not None:
        params["duration"] = duration_seconds
    if intensity_min is not None:
        params["intensityMin"] = intensity_min
    if intensity_max is not None:
        params["intensityMax"] = intensity_max
    if interval_type:
        params["type"] = interval_type
    if reps is not None:
        params["reps"] = reps
    if limit is not None:
        params["limit"] = limit

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities/interval-search",
        api_key=api_key,
        params=params if params else None,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error searching intervals: {result.get('message', 'Unknown error')}"

    activities = result if isinstance(result, list) else []
    formatted = [
        format_search_result(Activity.from_dict(a)) for a in activities if isinstance(a, dict)
    ]
    if not formatted:
        return "No activities found with matching intervals."

    return "Interval search results:\n\n" + "\n".join(formatted)
