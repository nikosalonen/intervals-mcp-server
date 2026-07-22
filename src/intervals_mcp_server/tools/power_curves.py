"""
Power curve MCP tools for Intervals.icu.

This module contains tools for retrieving athlete power curve data.
"""

import json
import logging
from datetime import datetime

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_power_curves
from intervals_mcp_server.utils.schemas import PowerCurve
from intervals_mcp_server.utils.validation import resolve_athlete_id, validate_date

from intervals_mcp_server.mcp_instance import mcp

logger = logging.getLogger(__name__)
config = get_config()

# 5s, 15s, 30s, 1min, 2min, 5min, 10min, 20min, 60min
DEFAULT_DURATIONS: tuple[int, ...] = (5, 15, 30, 60, 120, 300, 600, 1200, 3600)


def _validate_date_range(start_date: str | None, end_date: str | None) -> str | None:
    """Validate the optional custom date range; return an error message or None."""
    if (start_date is None) != (end_date is None):
        return "Error: Both start_date and end_date must be provided together for a custom date range."
    if start_date and end_date:
        try:
            validate_date(start_date)
            validate_date(end_date)
        except ValueError:
            return "Error: Dates must be in YYYY-MM-DD format."
        if datetime.strptime(start_date, "%Y-%m-%d") >= datetime.strptime(end_date, "%Y-%m-%d"):
            return "Error: start_date must be before end_date."
    return None


@mcp.tool()
async def get_athlete_power_curves(  # pylint: disable=too-many-arguments,too-many-return-statements,too-many-positional-arguments
    activity_type: str = "Ride",
    durations: list[int] | None = None,
    indoor_outdoor: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    this_season: bool = True,
    last_season: bool = True,
    include_normalised: bool = True,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get power curves (best power per duration) for an athlete from Intervals.icu.

    Returns the best power output for the selected durations across the selected
    time periods. Power values are in watts. Each duration line ends with the ID
    of the activity where the best value was set, in [brackets]; when the best
    W/kg was set in a different activity than the best watts, that activity's ID
    is appended separately as (W/kg: [id]). Durations without data are listed in
    a trailing "No data for:" note per curve.

    Args:
        activity_type: Activity type (e.g. "Ride", "Run", "VirtualRide"). Default "Ride".
        durations: Durations in seconds to include. Default [5, 15, 30, 60, 120, 300, 600, 1200, 3600].
        indoor_outdoor: Filter by location — "indoor" or "outdoor". Omit for no filtering.
        start_date: Start date (YYYY-MM-DD) for a custom date range curve. Requires end_date
            and must be strictly before it.
        end_date: End date (YYYY-MM-DD) for a custom date range curve. Requires start_date.
        this_season: Include this season's curve (default True).
        last_season: Include last season's curve (default True).
        include_normalised: Include weight-normalised W/kg values (default True).
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    if indoor_outdoor not in (None, "indoor", "outdoor"):
        return "Error: indoor_outdoor must be 'indoor', 'outdoor', or omitted."

    # Treat empty strings as omitted so they get the same validation as None
    start_date = start_date or None
    end_date = end_date or None

    date_error = _validate_date_range(start_date, end_date)
    if date_error:
        return date_error

    curve_keys: list[str] = []
    if this_season:
        curve_keys.append("s0")
    if last_season:
        curve_keys.append("s1")
    if start_date and end_date:
        curve_keys.append(f"r.{start_date}.{end_date}")
    if not curve_keys:
        return "Error: At least one curve must be selected (this_season, last_season, or a date range)."

    if durations is None:
        durations = list(DEFAULT_DURATIONS)

    params: dict[str, str] = {
        "curves": ",".join(curve_keys),
        "type": activity_type,
        "includeRanks": "false",  # rank data isn't parsed into PowerCurve
    }
    if indoor_outdoor:
        # The API's indoor filter takes the strings "indoor"/"outdoor", not a
        # boolean — booleans get a 422 "Indoor filter expected indoor/outdoor value"
        params["filters"] = json.dumps([{"field_id": "indoor", "value": indoor_outdoor, "id": 1}])

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/power-curves",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching power curves: {result.get('message', 'Unknown error')}"

    if isinstance(result, dict):
        curve_list = result.get("list")
    else:
        curve_list = result
    if not isinstance(curve_list, list):
        logger.error(
            "Unexpected power curves payload for athlete %s: got %s",
            athlete_id_to_use,
            type(result).__name__,
        )
        return "Error: Unexpected response from the power curves API."
    if not curve_list:
        return f"No power curve data found for athlete {athlete_id_to_use} ({activity_type})."

    try:
        curves = [PowerCurve.from_dict(c) for c in curve_list if isinstance(c, dict)]
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to parse power curve data: %s", e, exc_info=True)
        return "Error: Failed to parse power curve data."

    if not curves:
        return f"No power curve data found for athlete {athlete_id_to_use} ({activity_type})."

    return format_power_curves(curves, durations, include_normalised)
