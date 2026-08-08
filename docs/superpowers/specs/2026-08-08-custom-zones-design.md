# Custom Zone Support (CZ codes) — Design

Date: 2026-08-08

## Problem

Intervals.icu workout text references custom zones by code, e.g. `- 10m CZZ2 HR`. The MCP server
cannot resolve those codes to heart rates or watts, so it cannot verify or author workouts that use
them.

Two gaps cause this:

1. `get_sport_settings` returns the *standard* zone model (`hr_zones`, `power_zones`, `pace_zones`).
   Custom zones are not there. Mapping the standard `hr_zones` array onto `CZZ1`–`CZZ5` produces
   wrong heart rates.
2. `get_custom_items` lists custom items by id, name and type only. It never shows the zone bands
   held in a `ZONES` item's `content`.

## How custom zones actually work

Custom zone sets are custom items of type `ZONES`. Sport settings link to them by id:

```
GET /athlete/{id}/sport-settings
  → [ { types: ["Run","VirtualRun","TrailRun"], lthr: 170, ftp: null,
        custom_zones_ids: [945743], ... }, ... ]

GET /athlete/{id}/custom-item
  → [ { id: 945743, type: "ZONES", name: "8020 endurance",
        content: {
          code: "Endurance8020",
          anchor: "lthr",
          stream_type: "heartrate",
          round_zones_down: true,
          use_pace_units: false,
          zones: [
            { id: "Z1", name: "Zone 1", start: 0.72, end: 0.81, color: "..." },
            { id: "Z2", name: "Zone 2", start: 0.81, end: 0.90, color: "..." },
            ...
          ]
        } }, ... ]
```

Zone `start`/`end` are fractions of an anchor threshold. The workout-text code is `"CZ"` prefixed to
the zone's **`id`** — so `CZZ2` is `CZ` + `Z2`, and `CZMAF` is `CZ` + `MAF`. `content.code`
(`"Endurance8020"`) names the *set*, not the code used in workout text.

Verified against the athlete's real data, zone `Z2` of "8020 endurance" (0.81–0.90 of LTHR,
`round_zones_down: true`):

| LTHR | ⌊0.81 × LTHR⌋ | ⌊0.90 × LTHR⌋ | Observed CZZ2 |
| ---- | ------------- | ------------- | ------------- |
| 170  | 137           | 153           | 137–153       |
| 165  | 133           | 148           | 133–148       |

## Scope

Read and resolve only. Creating or editing custom zone sets is out of scope.

## Design

### Data flow

```
get_custom_zones(sport_type=None)
   |
   +-- GET /athlete/{id}/sport-settings   -> groups with types[], lthr, ftp, custom_zones_ids[]
   +-- GET /athlete/{id}/custom-item      -> all custom items; keep type == "ZONES"
        |
        +-- join on custom_zones_ids -> resolve(zone, anchor value) -> formatted table
        +-- leftover ZONES items     -> "Not attached to any sport" section, fractions only
```

Two existing endpoints, joined in the tool. No new endpoint.

### Schemas (`utils/schemas.py`)

Two new dataclasses following the existing `from_dict` convention:

```python
@dataclass
class CustomZone:
    id: str | None
    name: str | None
    start: float | None
    end: float | None
    color: str | None
    start_anchor: str | None
    end_anchor: str | None

@dataclass
class CustomZoneSet:
    item_id: int | None
    name: str | None            # custom item name, e.g. "8020 endurance"
    code: str | None            # content.code, e.g. "Endurance8020"
    anchor: str | None          # "lthr" | "ftp"
    stream_type: str | None     # "heartrate" | "watts"
    round_zones_down: bool
    use_pace_units: bool
    zones: list[CustomZone]
```

`CustomZoneSet.from_custom_item(item: dict)` builds one from a raw `custom-item` dict, reading
`content`. Items whose `type` is not `ZONES`, or whose `content.zones` is missing or not a list,
are rejected by returning `None` rather than raising.

Changes to the existing `AthleteSportSettings`:

- Add `types: list[str]`, `custom_zones_ids: list[int]`, `hr_zone_names: list[str]`,
  `power_zone_names: list[str]`, `pace_zone_names: list[str]`.
- **Bug fix:** the API returns `types` (an array); `from_dict` currently reads `data.get("type")`,
  so `format_sport_settings` prints `Sport: N/A` for every sport. `type` falls back to `types[0]`.

### Resolution (`utils/zones.py`, new module)

One pure function, no I/O:

```python
def resolve_zone_set(
    zone_set: CustomZoneSet,
    lthr: int | None,
    ftp: int | None,
) -> list[ResolvedZone]
```

`ResolvedZone` carries `code`, `name`, `start_pct`, `end_pct`, `start_value`, `end_value`, `unit`,
and `note`.

Rules:

- **Anchor per boundary.** Use `zone.start_anchor` if non-empty, else `zone_set.anchor`; likewise
  `zone.end_anchor`. Per-zone overrides occur in real data (the "80/20 Potencia" set has
  `start_anchor: "ftp"` on its top zone).
- **Anchor value.** `"lthr"` -> the sport group's `lthr` (unit `bpm`); `"ftp"` -> its `ftp`
  (unit `W`).
- **Rounding.** `round_zones_down: true` -> `math.floor`; otherwise `round`.
- **Code.** `"CZ" + zone.id`.
- **Missing anchor.** If the anchor threshold is `None` or `0`, leave `start_value`/`end_value` as
  `None` and set `note` naming the threshold to set. Never substitute a guess.
- **Unknown anchor name.** Treated as missing, with a note giving the unrecognised value.

Boundaries are reported as-is: `CZZ1` ends at 137 and `CZZ2` starts at 137. This matches what
Intervals.icu displays and the observed values above.

### Tool (`tools/athlete.py`)

```python
get_custom_zones(sport_type: str | None = None,
                 athlete_id: str | None = None,
                 api_key: str | None = None) -> str
```

`sport_type` matches case-insensitively against each group's `types` array (so `"TrailRun"` and
`"Run"` both select the Run group). Omitted, it reports every sport group that has a linked set,
then the unattached section.

Output:

```
Custom zones for Run (LTHR 170, anchor: lthr)
Set: 8020 endurance  [id 945743, heartrate]

  Code    Name      Range        bpm
  CZZ1    Zone 1    72-81%       122-137
  CZZ2    Zone 2    81-90%       137-153
  CZZX    Zone X    90-95%       153-161
  CZZ3    Zone 3    95-100%      161-170
  CZZY    Zone Y    100-102%     170-173
  CZZ4    Zone 4    102-105%     173-178
  CZZ5    Zone 5    105-130%     178-221

Use these codes in workout text: "- 10m CZZ2 HR"
```

Sports whose `custom_zones_ids` is empty are reported as having no custom zone set. `ZONES` items
not referenced by any sport group appear last:

```
Not attached to any sport
Set: 80/20 Potencia  [id 1012352, watts, anchor: ftp]
  CZZ1 Active Recovery 0-76%   |  CZZ2 Endurance 76-88%  |  ...
```

Fractions only for these — there is no sport threshold to resolve against, and the codes are not
usable in workout text until the set is attached.

### Changes to `get_sport_settings`

- Fix `Sport:` to render the sport group (`Run, VirtualRun, TrailRun`).
- Label the standard zones with the names already returned by the API and currently discarded
  (`hr_zone_names`, `power_zone_names`, `pace_zone_names`).
- Add one pointer line when the group links a set:
  `Custom zone sets: 8020 endurance (call get_custom_zones)`.

The full zone table stays out of `get_sport_settings`; with no `sport_type` it returns four sport
groups, and inlining four tables would bloat every call.

### Registration

Import `get_custom_zones` in `tools/__init__.py` and `server.py`, and add it to both `__all__`
lists and the docstring tool inventory, as the existing tools do.

### Error handling

Follows the module's existing convention: return an error string, never raise.

- Sport settings request fails -> `get_custom_zones` returns the error message.
- Custom item request fails -> `get_custom_zones` returns the error message; `get_sport_settings`
  degrades to its current output without the pointer line rather than failing.
- A `ZONES` item with malformed `content` is skipped and logged, and the remaining sets still
  render — matching how `get_sport_settings` already handles a bad sport entry.

## Testing

`resolve_zone_set` is pure, so it is tested directly:

- LTHR 170 -> `CZZ2` = 137–153, and LTHR 165 -> `CZZ2` = 133–148 (the verified cases above).
- Per-zone `start_anchor` override resolves against FTP while the set anchor is `lthr`.
- `round_zones_down: false` rounds to nearest rather than flooring.
- Missing `lthr` yields percentages with `None` values and a note.
- Unrecognised anchor name yields a note, not an exception.

Tool-level tests use the existing `monkeypatch.setattr` pattern against both
`api.client.make_intervals_request` and the tool module's imported reference, with fixtures in
`tests/sample_data.py` derived from the real payload shapes shown above (ids and values kept,
athlete identifiers replaced). They cover: sport with a linked set, sport with none, `sport_type`
matching an alias (`TrailRun`), the unattached-set section, and a custom-item fetch failure.

`AthleteSportSettings.from_dict` gets a regression test asserting `types` is parsed and `type`
falls back to `types[0]`.

## Out of scope

- Creating or editing custom zone sets (`PUT /custom-item/{id}`).
- Pace-anchored zone sets (`use_pace_units: true`). The field is parsed and carried on
  `CustomZoneSet`, but no pace resolution is implemented; such sets render as fractions with a note.
- `docs/training-plan-prompt.md` contains a live API key committed to git. Flagged here for
  visibility; rotating it and scrubbing history is separate work.
