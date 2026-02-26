# Intervals.icu API Reference for MCP Tool Development

Instructions for an LLM to implement MCP tools that wrap the Intervals.icu API in this project.

## Already Implemented Tools

The following tools already exist and should NOT be re-implemented:

**Activities** (`tools/activities.py`): `get_activities`, `get_activity_details`, `get_activity_intervals`, `get_activity_streams`

**Events** (`tools/events.py`): `get_events`, `get_event_by_id`, `delete_event`, `delete_events_by_date_range`, `add_or_update_event`

**Wellness** (`tools/wellness.py`): `get_wellness_data`

**Custom Items** (`tools/custom_items.py`): `get_custom_items`, `get_custom_item_by_id`, `create_custom_item`, `update_custom_item`, `delete_custom_item`

Note: The existing `delete_event` tool works for deleting seasons too (seasons are events), so no separate `delete_season` tool is needed.

## Tools to Implement

### Sport Settings / HR Zone Management (4 tools)

1. `list_sport_settings` — `GET /athlete/{athleteId}/sport-settings`
2. `get_sport_settings` — `GET /athlete/{athleteId}/sport-settings/{id}` (accepts type name like `Run`)
3. `update_sport_settings` — `PUT /athlete/{athleteId}/sport-settings/{id}?recalcHrZones=...`
4. `apply_sport_settings` — `PUT /athlete/{athleteId}/sport-settings/{id}/apply`

### Season Management (3 tools)

5. `list_seasons` — `GET /athlete/{id}/events` with `category=SEASON_START` and wide date range
6. `create_season` — `POST /athlete/{id}/events?upsertOnUid=false` with `category: "SEASON_START"` (existing `add_or_update_event` is hardcoded to `WORKOUT` category so cannot be used)
7. `update_season` — `PUT /athlete/{id}/events/{eventId}` (update name, date, color, description)

---

## Project Patterns

Tools go in `src/intervals_mcp_server/tools/`, use `@mcp.tool()` decorators, and call `make_intervals_request()` for all HTTP calls. All tools are async and return formatted strings.

```python
from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.mcp_instance import mcp
from intervals_mcp_server.utils.validation import resolve_athlete_id

config = get_config()

@mcp.tool()
async def my_tool(athlete_id: str | None = None, api_key: str | None = None) -> str:
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg
    result = await make_intervals_request(url=f"/athlete/{athlete_id_to_use}/...", api_key=api_key)
    if isinstance(result, dict) and "error" in result:
        return f"Error: {result.get('message', 'Unknown error')}"
    # format and return string
```

`make_intervals_request` signature:

```python
async def make_intervals_request(
    url: str,                              # path after base URL, e.g. "/athlete/{id}/custom-item"
    api_key: str | None = None,
    params: dict[str, Any] | None = None,  # query params
    method: str = "GET",                   # GET, POST, PUT, DELETE
    data: dict[str, Any] | None = None,    # JSON body for POST/PUT
) -> dict[str, Any] | list[dict[str, Any]]
```

Register new tool modules by importing them in `server.py`.

---

## Sport Settings (HR zones, linking, applying)

Sport settings define HR zones, power zones, pace zones, and link custom zone items to activity types.

### SportSettings schema (HR zone-relevant fields)

```json
{
  "id": 1,                              // int32
  "athlete_id": "i123",                 // string
  "types": ["Run"],                     // string[] — activity type enum values
  "lthr": 170,                          // int32 — lactate threshold HR (bpm)
  "max_hr": 195,                        // int32 — max heart rate (bpm)
  "hr_zones": [120, 140, 155, 170, 185], // int32[] — zone boundaries (bpm)
  "hr_zone_names": ["Z1","Z2","Z3","Z4","Z5"], // string[]
  "hr_load_type": "HR_ZONES",           // enum: AVG_HR | HR_ZONES | HRSS
  "custom_zones_ids": [123, 456],       // int32[] — linked CustomItem IDs (type ZONES)
  "tiz_order": "HR_POWER_PACE",         // enum — time-in-zones display order
  "load_order": "HR_POWER_PACE",        // enum — training load priority
  "workout_order": "HR_POWER_PACE",     // enum — workout target display order
  "ftp": 250,                           // int32 — functional threshold power
  "power_zones": [150, 200, 250, 300, 350], // int32[]
  "power_zone_names": [...],            // string[]
  "threshold_pace": 4.5,                // float — threshold pace
  "pace_zones": [...],                  // float[]
  "pace_zone_names": [...],             // string[]
  "warmup_time": 600,                   // int32 — seconds
  "cooldown_time": 300                  // int32 — seconds
}
```

Order enums: `POWER_HR_PACE | POWER_PACE_HR | HR_POWER_PACE | HR_PACE_POWER | PACE_POWER_HR | PACE_HR_POWER`

### Sport Settings endpoints

| Method | Path | Query Params | Description | Body | Response |
|--------|------|-------------|-------------|------|----------|
| `GET` | `/api/v1/athlete/{athleteId}/sport-settings` | — | List all sport settings | — | `SportSettings[]` |
| `POST` | `/api/v1/athlete/{athleteId}/sport-settings` | — | Create sport settings with defaults | `SportSettings` | `SportSettings` |
| `GET` | `/api/v1/athlete/{athleteId}/sport-settings/{id}` | — | Get by numeric ID or type name (e.g. `Run`) | — | `SportSettings` |
| `PUT` | `/api/v1/athlete/{athleteId}/sport-settings/{id}` | `recalcHrZones` (bool, **required**) | Update sport settings | `SportSettings` | `SportSettings` |
| `PUT` | `/api/v1/athlete/{athleteId}/sport-settings` | — | Update multiple sport settings | `SportSettings[]` | `SportSettings[]` |
| `DELETE` | `/api/v1/athlete/{athleteId}/sport-settings/{id}` | — | Delete sport settings | — | `200 OK` |
| `PUT` | `/api/v1/athlete/{athleteId}/sport-settings/{id}/apply` | — | Apply settings to matching activities (async) | — | `object` |
| `GET` | `/api/v1/athlete/{athleteId}/sport-settings/{id}/matching-activities` | — | List activities matching the settings | — | activity list |

When `recalcHrZones=true`, the API auto-recalculates `hr_zones` from `lthr`/`max_hr`.

---

## Season Management

Seasons in Intervals.icu are **events** with `category: "SEASON_START"`. They are created, read, updated, and deleted using the standard Events API. The season start date marks the boundary of a training season (referenced in curve queries as `s0` = current season, `s1` = previous season, etc.).

### Event schema (season-relevant fields)

```json
{
  "id": 456,                        // int32, server-assigned
  "athlete_id": "i123",             // string
  "category": "SEASON_START",       // enum — MUST be "SEASON_START" for seasons
  "start_date_local": "2025-11-01T00:00:00", // string — season start date
  "end_date_local": "2026-03-31",   // string — optional end date
  "name": "Winter Base Season",     // string — season name
  "description": "...",             // string — optional
  "color": "#FF5733",               // string — optional, display color
  "not_on_fitness_chart": false,     // boolean
  "show_as_note": false,            // boolean
  "show_on_ctl_line": false,        // boolean
  "tags": ["base", "indoor"],       // string[] — optional
  "updated": "2024-01-01T00:00:00Z"
}
```

Full Event category enum: `WORKOUT | RACE_A | RACE_B | RACE_C | NOTE | PLAN | HOLIDAY | SICK | INJURED | SET_EFTP | FITNESS_DAYS | SEASON_START | TARGET | SET_FITNESS`

### EventEx schema (input for create/update)

Extends Event with additional fields for creation:

```json
{
  // ... all Event fields, plus:
  "uid": "unique-id",              // string — for upsert matching
  "file_contents": "...",          // string — workout file (zwo, mrc, erg, fit)
  "file_contents_base64": "...",   // string — base64-encoded workout file
  "filename": "workout.zwo",      // string
  "workout": {},                   // Workout object reference
  "plan_athlete_id": "...",        // string — plan linkage
  "plan_folder_id": 1,             // int32
  "plan_workout_id": 2,            // int32
  "load_target": 100,              // int32
  "time_target": 3600,             // int32
  "distance_target": 10000.0,      // float
  "external_id": "ext-123",        // string — for OAuth app upsert
  "sub_type": "NONE",              // enum: NONE | COMMUTE | WARMUP | COOLDOWN | RACE
  "target": "AUTO"                 // enum: AUTO | POWER | HR | PACE
}
```

### Season / Event endpoints

| Method | Path | Query Params | Description | Body | Response |
|--------|------|-------------|-------------|------|----------|
| `GET` | `/api/v1/athlete/{id}/events{format}` | `oldest`, `newest`, `category`, `limit`, `calendar_id`, `resolve` | List events. Use `category=SEASON_START` to list only seasons. `{format}` can be empty or `.csv`. | — | `Event[]` |
| `GET` | `/api/v1/athlete/{id}/events/{eventId}` | — | Get single event/season | — | `Event` |
| `POST` | `/api/v1/athlete/{id}/events` | `upsertOnUid` (bool, **required**) | Create event/season | `EventEx` | `Event` |
| `PUT` | `/api/v1/athlete/{id}/events/{eventId}` | — | Update event/season | `EventEx` | `Event` |
| `DELETE` | `/api/v1/athlete/{id}/events/{eventId}` | `others` (bool), `notBefore` (date) | Delete event/season | — | `object` |
| `POST` | `/api/v1/athlete/{id}/events/bulk` | — | Create multiple events | `EventEx[]` | `Event[]` |
| `PUT` | `/api/v1/athlete/{id}/events/bulk-delete` | — | Bulk delete by id or external_id | body with ids | `DeleteEventsResponse` |

### Season query example

```
GET /api/v1/athlete/{id}/events?oldest=2020-01-01&newest=2030-01-01&category=SEASON_START
```

### Season create example

```
POST /api/v1/athlete/{id}/events?upsertOnUid=false
{
  "category": "SEASON_START",
  "start_date_local": "2025-11-01T00:00:00",
  "name": "Winter Base Season",
  "description": "Base building phase",
  "color": "#3498db"
}
```

### Season references in curve queries

Seasons partition the timeline for performance curves. When querying power/HR/pace curves:
- `s0` = current season (from most recent `SEASON_START` to now)
- `s1` = previous season, `s2` = season before that, etc.

---

## Athlete Endpoint

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| `GET` | `/api/v1/athlete/{id}` | Get athlete with `sportSettings` and `custom_items` arrays | `WithSportSettings` |

---

## Activity Zone Data (read-only)

Activities contain these HR zone fields:
- `icu_hr_zones` — `int32[]` (zone boundaries bpm)
- `icu_hr_zone_times` — `int32[]` (seconds per zone)
- `custom_zones` — `ZoneSet[]` (custom zone time-in-zone results)
- `has_heartrate` — boolean
- `average_heartrate`, `max_heartrate` — numeric

### ZoneSet

```json
{
  "code": "custom_zone_code",
  "zones": [
    { "id": "z1", "start": 0.0, "end": 0.5, "start_value": 100.0, "end_value": 140.0, "secs": 600 }
  ]
}
```

### ZoneInfo

```json
{ "id": "z1", "start": 0.0, "end": 0.5, "start_value": 100.0, "end_value": 140.0, "secs": 600 }
```

- `start`/`end` — fraction (0.0–1.0)
- `start_value`/`end_value` — absolute bpm
- `secs` — time in zone (seconds)

### ZoneTime

```json
{ "id": "z1", "secs": 600 }
```

### Activity HR endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/activity/{id}/time-at-hr` | Time at heart rate data |
| `GET` | `/api/v1/activity/{id}/hr-curve{ext}` | HR curve (`.json` or `.csv`) |
| `GET` | `/api/v1/activity/{id}/hr-histogram` | HR histogram |

---

## Activity Type Enum

`Ride`, `Run`, `Swim`, `WeightTraining`, `Hike`, `Walk`, `AlpineSki`, `BackcountrySki`, `Badminton`, `Canoeing`, `Crossfit`, `EBikeRide`, `EMountainBikeRide`, `Elliptical`, `Golf`, `GravelRide`, `TrackRide`, `Handcycle`, `HighIntensityIntervalTraining`, `Hockey`, `IceSkate`, `InlineSkate`, `Kayaking`, `Kitesurf`, `MountainBikeRide`, `NordicSki`, `OpenWaterSwim`, `Padel`, `Pilates`, `Pickleball`, `Racquetball`, `Rugby`, `RockClimbing`, `RollerSki`, `Rowing`, `Sail`, `Skateboard`, `Snowboard`, `Snowshoe`, `Soccer`, `Squash`, `StairStepper`, `StandUpPaddling`, `Surfing`, `TableTennis`, `Tennis`, `TrailRun`, `Transition`, `Velomobile`, `VirtualRide`, `VirtualRow`, `VirtualRun`, `VirtualSki`, `WaterSport`, `Wheelchair`, `Windsurf`, `Workout`, `Yoga`, `Other`

