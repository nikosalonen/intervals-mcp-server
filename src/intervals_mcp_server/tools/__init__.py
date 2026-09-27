"""
MCP tools registry for Intervals.icu MCP Server.

Importing this package registers every tool: each module's @mcp.tool()
decorators run against the shared instance from mcp_instance.py.
"""

# Import all tools for re-export
# Note: Tools register themselves via @mcp.tool() decorators when imported
from intervals_mcp_server.tools.activities import (
    get_activities,
    get_activity_details,
    get_activity_intervals,
    get_activity_streams,
)
from intervals_mcp_server.tools.events import (
    add_or_update_event,
    delete_event,
    delete_events_by_date_range,
    get_event_by_id,
    get_events,
)
from intervals_mcp_server.tools.wellness import get_wellness_data
from intervals_mcp_server.tools.custom_items import (
    create_custom_item,
    delete_custom_item,
    get_custom_item_by_id,
    get_custom_items,
    update_custom_item,
)
from intervals_mcp_server.tools.athlete import get_athlete, get_sport_settings
from intervals_mcp_server.tools.gear import get_gear_list
from intervals_mcp_server.tools.power_curves import get_athlete_power_curves
from intervals_mcp_server.tools.search import search_activities, search_intervals
from intervals_mcp_server.tools.workouts import (
    create_bulk_workouts,
    list_folders,
    list_workouts,
)


__all__ = [
    "get_activities",
    "get_activity_details",
    "get_activity_intervals",
    "get_activity_streams",
    "get_events",
    "get_event_by_id",
    "delete_event",
    "delete_events_by_date_range",
    "add_or_update_event",
    "get_wellness_data",
    "get_custom_items",
    "get_custom_item_by_id",
    "create_custom_item",
    "update_custom_item",
    "delete_custom_item",
    "get_athlete",
    "get_sport_settings",
    "get_gear_list",
    "get_athlete_power_curves",
    "search_activities",
    "search_intervals",
    "list_workouts",
    "list_folders",
    "create_bulk_workouts",
]
