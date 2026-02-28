"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data.
"""

import logging

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_wellness_entry
from intervals_mcp_server.utils.schemas import WellnessEntry
from intervals_mcp_server.utils.validation import resolve_athlete_id, resolve_date_params

from intervals_mcp_server.mcp_instance import mcp

logger = logging.getLogger(__name__)
config = get_config()


@mcp.tool()
async def get_wellness_data(
    athlete_id: str | None = None,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Get wellness data for an athlete from Intervals.icu

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    """
    # Resolve athlete ID and date parameters
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    start_date, end_date = resolve_date_params(start_date, end_date)

    # Call the Intervals.icu API
    params = {"oldest": start_date, "newest": end_date}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching wellness data: {result.get('message')}"

    # Format the response
    if not result:
        return (
            f"No wellness data found for athlete {athlete_id_to_use} in the specified date range."
        )

    wellness_summary = "Wellness Data:\n\n"
    entries_processed = 0

    # Handle both list and dictionary responses
    if isinstance(result, dict):
        for date_str, data in result.items():
            if isinstance(data, dict):
                # Ensure the date key is set so WellnessEntry.id is populated
                entry_data = data if "id" in data else {**data, "id": date_str}
                try:
                    wellness_summary += (
                        format_wellness_entry(WellnessEntry.from_dict(entry_data)) + "\n\n"
                    )
                    entries_processed += 1
                except (TypeError, KeyError, ValueError) as e:
                    logger.error("Failed to format wellness entry for %s: %s", date_str, e, exc_info=True)
                    wellness_summary += f"[Wellness data for {date_str}: failed to format]\n\n"
                    entries_processed += 1
    elif isinstance(result, list):
        for entry in result:
            if isinstance(entry, dict):
                try:
                    wellness_summary += (
                        format_wellness_entry(WellnessEntry.from_dict(entry)) + "\n\n"
                    )
                    entries_processed += 1
                except (TypeError, KeyError, ValueError) as e:
                    entry_id = entry.get("id", "unknown")
                    logger.error("Failed to format wellness entry %s: %s", entry_id, e, exc_info=True)
                    wellness_summary += f"[Wellness data for {entry_id}: failed to format]\n\n"
                    entries_processed += 1

    if entries_processed == 0:
        wellness_summary += "[No wellness data found]\n\n"

    return wellness_summary
