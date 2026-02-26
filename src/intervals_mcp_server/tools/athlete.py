"""
Athlete profile and sport settings MCP tools for Intervals.icu.

This module contains tools for retrieving athlete profile and sport settings (FTP, zones, etc.).
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_athlete_summary, format_sport_settings
from intervals_mcp_server.utils.schemas import Athlete, AthleteSportSettings
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool()
async def get_athlete(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get athlete profile (weight, resting HR, location, timezone, status) from Intervals.icu.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}",
        api_key=api_key,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching athlete: {result.get('message', 'Unknown error')}"

    if not isinstance(result, dict):
        return "Unexpected response from API."

    return format_athlete_summary(Athlete.from_dict(result))


@mcp.tool()
async def get_sport_settings(
    athlete_id: str | None = None,
    sport_type: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get sport settings (FTP, zones, LTHR, max HR, pace thresholds, warmup/cooldown) for an athlete.

    Returns all sport types if sport_type is omitted, or a single sport's settings if sport_type is provided (e.g. 'Run', 'Ride').

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        sport_type: Optional sport type to return only that sport's settings.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    url = f"/athlete/{athlete_id_to_use}/sport-settings"
    if sport_type:
        url = f"{url}/{sport_type}"

    result = await make_intervals_request(url=url, api_key=api_key)

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching sport settings: {result.get('message', 'Unknown error')}"

    if sport_type:
        if not isinstance(result, dict):
            return "Unexpected response from API."
        return format_sport_settings(AthleteSportSettings.from_dict(result))

    # All sports: result is a list or dict of sport settings
    if isinstance(result, list):
        return "\n\n---\n\n".join(
            format_sport_settings(AthleteSportSettings.from_dict(s))
            for s in result
            if isinstance(s, dict)
        )
    if isinstance(result, dict):
        return "\n\n---\n\n".join(
            format_sport_settings(AthleteSportSettings.from_dict(s))
            for s in result.values()
            if isinstance(s, dict)
        )
    return "No sport settings found."
