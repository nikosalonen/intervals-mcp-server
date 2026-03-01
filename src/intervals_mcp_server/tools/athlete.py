"""
Athlete profile and sport settings MCP tools for Intervals.icu.

This module contains tools for retrieving athlete profile and sport settings (FTP, zones, etc.).
"""

import logging

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import (
    format_athlete_summary,
    format_sport_settings,
    format_training_plan,
)
from intervals_mcp_server.utils.schemas import Athlete, AthleteSportSettings, AthleteTrainingPlan
from intervals_mcp_server.utils.validation import resolve_athlete_id

from intervals_mcp_server.mcp_instance import mcp

logger = logging.getLogger(__name__)
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

    try:
        return format_athlete_summary(Athlete.from_dict(result))
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to parse athlete data: %s", e, exc_info=True)
        return "Error: Failed to parse athlete data."


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
        try:
            return format_sport_settings(AthleteSportSettings.from_dict(result))
        except (TypeError, KeyError, ValueError) as e:
            logger.error("Failed to parse sport settings: %s", e, exc_info=True)
            return "Error: Failed to parse sport settings."

    # All sports: result is a list or dict of sport settings
    items = (
        result
        if isinstance(result, list)
        else list(result.values()) if isinstance(result, dict) else []
    )
    formatted: list[str] = []
    for s in items:
        if isinstance(s, dict):
            try:
                formatted.append(format_sport_settings(AthleteSportSettings.from_dict(s)))
            except (TypeError, KeyError, ValueError) as e:
                sport_name = s.get("type", "Unknown")
                logger.error("Failed to format sport setting for %s: %s", sport_name, e, exc_info=True)
                formatted.append(f"[Sport setting '{sport_name}': failed to format]")
    return "\n\n---\n\n".join(formatted) if formatted else "No sport settings found."


@mcp.tool()
async def get_training_plan(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get the athlete's current training plan from Intervals.icu.

    Returns the training plan with its workouts, including day offsets, sport types, and durations.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/training-plan",
        api_key=api_key,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching training plan: {result.get('message', 'Unknown error')}"

    if not isinstance(result, dict):
        return "No training plan found."

    try:
        return format_training_plan(AthleteTrainingPlan.from_dict(result))
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to parse training plan data: %s", e, exc_info=True)
        return "Error: Failed to parse training plan data."
