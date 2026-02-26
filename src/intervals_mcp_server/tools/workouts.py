"""
Workout library and bulk create MCP tools for Intervals.icu.

This module contains tools for listing workouts, folders, and creating workouts in bulk.
"""

import logging

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_folder_summary, format_workout
from intervals_mcp_server.utils.schemas import Folder, Workout
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

logger = logging.getLogger(__name__)
config = get_config()


@mcp.tool()
async def list_workouts(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """List all workouts in the athlete's workout library.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/workouts",
        api_key=api_key,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error listing workouts: {result.get('message', 'Unknown error')}"

    workouts = result if isinstance(result, list) else []
    if not workouts:
        return "No workouts in library."

    formatted = []
    for w in workouts:
        if isinstance(w, dict):
            try:
                formatted.append(format_workout(Workout.from_dict(w)).strip())
            except (TypeError, KeyError, ValueError) as e:
                logger.warning("Failed to format workout: %s", e)
    return "Workout library:\n\n" + "\n".join(formatted) if formatted else "No workouts in library."


@mcp.tool()
async def list_folders(
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """List workout folders with their child workouts.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/folders",
        api_key=api_key,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error listing folders: {result.get('message', 'Unknown error')}"

    folders = result if isinstance(result, list) else []
    if not folders:
        return "No folders found."

    formatted = []
    for f in folders:
        if isinstance(f, dict):
            try:
                formatted.append(format_folder_summary(Folder.from_dict(f)))
            except (TypeError, KeyError, ValueError) as e:
                logger.warning("Failed to format folder: %s", e)
    return "Folders:\n\n" + "\n\n".join(formatted) if formatted else "No folders found."


@mcp.tool()
async def create_bulk_workouts(
    athlete_id: str | None = None,
    workouts: list[dict] | None = None,
    api_key: str | None = None,
) -> str:
    """Create multiple workouts at once in the athlete's library.

    Pass a list of workout objects (each with name, sport, intervals, etc. as per Intervals.icu API).

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, uses ATHLETE_ID from env if not provided).
        workouts: List of workout objects to create.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    if not workouts:
        return "No workouts provided. Pass a list of workout objects to create."

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/workouts/bulk",
        api_key=api_key,
        method="POST",
        data=workouts,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error creating bulk workouts: {result.get('message', 'Unknown error')}"

    created = result if isinstance(result, list) else []
    return f"Successfully created {len(created)} workout(s)."
