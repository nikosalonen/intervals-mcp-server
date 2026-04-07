"""
Athlete profile and sport settings MCP tools for Intervals.icu.

This module contains tools for retrieving athlete profile and sport settings (FTP, zones, etc.).
"""

import logging
from typing import Any

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
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
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
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
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
async def update_sport_settings(
    sport_type: str,
    lthr: int | None = None,
    ftp: int | None = None,
    max_hr: int | None = None,
    warmup_time: int | None = None,
    cooldown_time: int | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Update sport settings (LTHR, FTP, max HR, warmup/cooldown) for a given sport type.

    Only the fields you provide are updated; all others are left unchanged.
    Zone arrays are not supported — set thresholds and let Intervals.icu recalculate zones.

    Args:
        sport_type: The sport type to update (e.g. 'Run', 'Ride', 'Swim'). Required.
        lthr: Lactate threshold heart rate in bpm (must be > 0).
        ftp: Functional threshold power in watts (must be > 0).
        max_hr: Maximum heart rate in bpm (must be > 0).
        warmup_time: Warmup duration in seconds (must be >= 0).
        cooldown_time: Cooldown duration in seconds (must be >= 0).
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    if not isinstance(sport_type, str) or not sport_type.strip():
        return "Error: sport_type must be a non-empty string."
    sport_type = sport_type.strip()

    settings: dict[str, Any] = {}

    for value, api_field, label, min_val in [
        (lthr, "lthr", "lthr", 1),
        (ftp, "ftp", "ftp", 1),
        (max_hr, "maxHr", "max_hr", 1),
        (warmup_time, "warmup", "warmup_time", 0),
        (cooldown_time, "cooldown", "cooldown_time", 0),
    ]:
        if value is not None:
            if not isinstance(value, int) or isinstance(value, bool) or value < min_val:
                qualifier = "positive" if min_val > 0 else "non-negative"
                return f"Error: {label} must be a {qualifier} integer."
            settings[api_field] = value

    if not settings:
        return "Error: At least one setting must be provided."

    settings["type"] = sport_type

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/sport-settings/{sport_type}",
        api_key=api_key,
        method="PUT",
        data=settings,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error updating sport settings: {result.get('message', 'Unknown error')}"

    if not isinstance(result, dict):
        logger.error(
            "update_sport_settings: unexpected response type %s for sport_type=%r: %r",
            type(result).__name__,
            sport_type,
            result,
        )
        return "Error updating sport settings: unexpected response."

    try:
        return "Sport settings updated successfully:\n" + format_sport_settings(
            AthleteSportSettings.from_dict(result)
        )
    except (TypeError, KeyError, ValueError) as e:
        logger.error(
            "Failed to format updated sport settings for sport_type=%r, result=%r: %s",
            sport_type,
            result,
            e,
            exc_info=True,
        )
        return "Sport settings updated but failed to format response."


@mcp.tool()
async def get_training_plan(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get the athlete's current training plan from Intervals.icu.

    Returns the training plan with its workouts, including day offsets, sport types, and durations.

    Args:
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
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
