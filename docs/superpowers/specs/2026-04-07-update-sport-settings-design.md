# Design: `update_sport_settings` Tool

**Date:** 2026-04-07
**Status:** Approved

## Summary

Add a `update_sport_settings` MCP tool that allows writing sport setting scalars (LTHR, FTP, max HR, warmup/cooldown times) for a given sport type. Complements the existing `get_sport_settings` read tool.

## Motivation

The MCP server currently supports reading sport settings but has no way to update them. The primary use case is updating LTHR after a threshold test, but FTP, max HR, and warmup/cooldown times are equally useful to update.

## Tool Signature

```python
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
) -> str
```

- `sport_type` is required (e.g. `"Run"`, `"Ride"`, `"Swim"`).
- All value fields are optional. Only non-`None` values are included in the request body.
- At least one value field must be provided; the tool returns an error string if none are.
- `athlete_id` and `api_key` follow the server convention (use configured values if not provided).

## API Call

`PUT /athlete/{id}/sport-settings/{sport_type}`

Request body: JSON object containing only the fields the caller provided (partial update). Uses the existing `make_intervals_request(method="PUT", data=...)` pattern.

## Out of Scope

Zone arrays (`power_zones`, `hr_zones`, `pace_zones`) are not supported. Users set thresholds and let Intervals.icu recalculate zones automatically.

## Response Formatting

On success: `"Sport settings updated successfully:\n" + format_sport_settings(AthleteSportSettings.from_dict(result))`

On API error: `"Error updating sport settings: <message>"`

On validation error (no fields provided): `"Error: at least one setting must be provided."`

Reuses existing `AthleteSportSettings.from_dict()` and `format_sport_settings()` — no new formatting or schema code needed.

## File Changes

- **`src/intervals_mcp_server/tools/athlete.py`** — add `update_sport_settings` function alongside `get_sport_settings`. No new files.

## Testing

Two tests in `tests/test_server.py`:

1. **Success** — monkeypatched API returns updated settings dict; assert result contains `"Sport settings updated successfully"` and expected field values.
2. **Error** — monkeypatched API returns `{"error": True, "message": "..."}`: assert result contains `"Error updating sport settings"`.

Follows the same monkeypatch pattern as `test_update_custom_item` and `test_update_season`.
