"""
Gear MCP tools for Intervals.icu.

Activity payloads from Intervals.icu carry only the gear ID (e.g. "b16177481");
the gear name lives in the separate /athlete/{id}/gear endpoint. This module
caches the gear catalog per athlete for the lifetime of the MCP process so
activity tools can resolve names without an extra API round-trip per activity.
Pass refresh=True to get_gear_list to re-fetch.
"""

import logging

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import format_gear_list
from intervals_mcp_server.utils.schemas import Gear
from intervals_mcp_server.utils.validation import resolve_athlete_id

from intervals_mcp_server.mcp_instance import mcp

logger = logging.getLogger(__name__)
config = get_config()

# Gear catalog per athlete, cached for the process lifetime.
_gear_cache: dict[str, list[Gear]] = {}


async def _fetch_gear_catalog(
    athlete_id: str,
    api_key: str | None = None,
    refresh: bool = False,
) -> list[Gear] | str:
    """Return the gear catalog for an athlete, from cache unless refresh is set.

    Returns an error string when the API call or parsing fails.
    """
    if not refresh and athlete_id in _gear_cache:
        return _gear_cache[athlete_id]

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/gear",
        api_key=api_key,
    )

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching gear: {result.get('message', 'Unknown error')}"

    if not isinstance(result, list):
        return "Unexpected response from API."

    try:
        catalog = [Gear.from_dict(item) for item in result if isinstance(item, dict)]
    except (TypeError, KeyError, ValueError) as e:
        logger.error("Failed to parse gear data: %s", e, exc_info=True)
        return "Error: Failed to parse gear data."

    _gear_cache[athlete_id] = catalog
    return catalog


async def get_gear_name_map(athlete_id: str, api_key: str | None = None) -> dict[str, str]:
    """Return a {gear_id: gear_name} lookup for an athlete.

    Returns an empty dict on any error so activity formatting degrades
    gracefully to showing the bare gear ID.
    """
    if not athlete_id:
        return {}
    catalog = await _fetch_gear_catalog(athlete_id, api_key=api_key)
    if isinstance(catalog, str):
        return {}
    return {item.id: item.name for item in catalog if item.id and item.name}


@mcp.tool()
async def get_gear_list(
    athlete_id: str | None = None,
    api_key: str | None = None,
    refresh: bool = False,
) -> str:
    """Get the gear catalog (bikes, shoes, etc.) for an athlete from Intervals.icu.

    The catalog is cached for the MCP process lifetime; pass refresh=True to re-fetch.

    Args:
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
        refresh: If True, bypass the cache and re-fetch from the API (default False).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    catalog = await _fetch_gear_catalog(athlete_id_to_use, api_key=api_key, refresh=refresh)
    if isinstance(catalog, str):
        return catalog

    if not catalog:
        return f"No gear found for athlete {athlete_id_to_use}."

    return format_gear_list(catalog)
