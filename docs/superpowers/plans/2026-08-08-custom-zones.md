# Custom Zone (CZ code) Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the MCP server resolve Intervals.icu custom zone codes (`CZZ2`, `CZMAF`) to concrete heart rates and watts, via a new `get_custom_zones` tool.

**Architecture:** Custom zone sets are custom items of type `ZONES`; sport settings link to them by id through `custom_zones_ids`. Zone bands are stored as fractions of an anchor threshold (`lthr` or `ftp`). The new tool fetches both endpoints, joins them, and resolves fractions to values using a pure function in a new `utils/zones.py`. Formatting lives in `utils/formatting.py` alongside the existing `format_*` functions.

**Tech Stack:** Python 3.12+, FastMCP, httpx, dataclasses, pytest, ruff, mypy. Managed with `uv`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-08-custom-zones-design.md`. Read it before Task 1.
- Run every tool through `uv run` — `uv run pytest`, `uv run ruff check .`, `uv run mypy src tests`.
- All three checks (ruff, mypy, pytest) must pass before each commit.
- Never mention Claude in commit messages. No `Co-Authored-By` trailers.
- Commit messages use conventional-commit prefixes (`feat:`, `fix:`, `test:`, `refactor:`), matching this repo's history.
- Tools return formatted strings and never raise; parse failures are logged and degrade to a message.
- MCP tools are `async` and decorated with `@mcp.tool()`.
- The workout-text code for a zone is `"CZ"` + the zone's `id` field. `content.code` names the *set* and is NOT the workout-text code.
- Do not modify `docs/training-plan-prompt.md`. Its committed API key is a known, separately-tracked issue.

## File Structure

| File | Responsibility |
| ---- | -------------- |
| `src/intervals_mcp_server/utils/schemas.py` (modify) | Add `CustomZone`, `CustomZoneSet`, `_as_float`; extend `AthleteSportSettings` |
| `src/intervals_mcp_server/utils/zones.py` (create) | `ResolvedZone` + pure `resolve_zone_set()` — fraction → bpm/watts. No I/O |
| `src/intervals_mcp_server/utils/formatting.py` (modify) | `format_custom_zone_set`, `format_unattached_zone_set`; enrich `format_sport_settings` |
| `src/intervals_mcp_server/tools/athlete.py` (modify) | `get_custom_zones` tool + private join helpers |
| `src/intervals_mcp_server/tools/__init__.py`, `server.py` (modify) | Register the new tool |
| `tests/test_zones.py` (create) | Unit tests for the pure resolver |
| `tests/test_schemas.py`, `tests/test_formatting.py`, `tests/test_server.py`, `tests/sample_data.py` (modify) | Schema, formatting, tool-level tests and fixtures |

---

### Task 1: Extend `AthleteSportSettings` and fix the `types` bug

The Intervals.icu API returns `types` (an array of sport names), but `from_dict` reads
`data.get("type")`. Every sport currently renders as `Sport: N/A`. This task fixes that and adds
the fields the rest of the plan needs.

**Files:**
- Modify: `src/intervals_mcp_server/utils/schemas.py` (the `AthleteSportSettings` dataclass, around line 704)
- Test: `tests/test_schemas.py` (append to the `AthleteSportSettings` section, around line 201)

**Interfaces:**
- Consumes: existing module helpers `_first`, `_get_list`, `_safe_enum`, and the `SportType` enum.
- Produces: `AthleteSportSettings` with new attributes `types: list[str]`,
  `custom_zones_ids: list[int]`, `hr_zone_names: list[str]`, `power_zone_names: list[str]`,
  `pace_zone_names: list[str]`; `type` now falls back to `types[0]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_schemas.py`:

```python
def test_athlete_sport_settings_parses_types_array():
    """from_dict() reads the API's `types` array and derives `type` from it."""
    data = {
        "types": ["Run", "VirtualRun", "TrailRun"],
        "lthr": 170,
        "custom_zones_ids": [945743],
        "hr_zones": [122, 137, 153],
        "hr_zone_names": ["Recovery", "Aerobic", "Tempo"],
    }
    s = AthleteSportSettings.from_dict(data)
    assert s.types == ["Run", "VirtualRun", "TrailRun"]
    assert s.type == "Run"
    assert s.custom_zones_ids == [945743]
    assert s.hr_zone_names == ["Recovery", "Aerobic", "Tempo"]


def test_athlete_sport_settings_type_key_takes_precedence():
    """An explicit `type` key wins over `types[0]` so older payloads still parse."""
    s = AthleteSportSettings.from_dict({"type": "Ride", "types": ["Run"]})
    assert s.type == "Ride"


def test_athlete_sport_settings_defaults_are_empty_lists():
    """Missing list fields default to empty lists, never None."""
    s = AthleteSportSettings.from_dict({})
    assert s.types == []
    assert s.custom_zones_ids == []
    assert s.power_zone_names == []
    assert s.pace_zone_names == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -k athlete_sport_settings -v`

Expected: FAIL with `AttributeError: 'AthleteSportSettings' object has no attribute 'types'`.

- [ ] **Step 3: Implement**

In `src/intervals_mcp_server/utils/schemas.py`, replace the `AthleteSportSettings` dataclass body
and `from_dict` with:

```python
@dataclass
class AthleteSportSettings:
    """Athlete sport settings — FTP, zones, LTHR, pacing, warmup/cooldown."""

    type: str | None = None
    types: list[str] = field(default_factory=list)
    ftp: int | None = None
    lthr: int | None = None
    max_hr: int | None = None
    power_zones: list[int] = field(default_factory=list)
    hr_zones: list[int] = field(default_factory=list)
    pace_zones: list[float] = field(default_factory=list)
    power_zone_names: list[str] = field(default_factory=list)
    hr_zone_names: list[str] = field(default_factory=list)
    pace_zone_names: list[str] = field(default_factory=list)
    custom_zones_ids: list[int] = field(default_factory=list)
    warmup_time: int | None = None
    cooldown_time: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AthleteSportSettings":
        """Create an AthleteSportSettings from a raw API response dict."""
        types = [str(t) for t in _get_list(data, "types") if t is not None]
        return cls(
            type=_safe_enum(SportType, _first(data.get("type"), types[0] if types else None)),
            types=types,
            ftp=data.get("ftp"),
            lthr=data.get("lthr"),
            max_hr=_first(data.get("max_hr"), data.get("maxHr")),
            power_zones=_get_list(data, "power_zones", "zones", "powerZones"),
            hr_zones=_get_list(data, "hr_zones"),
            pace_zones=_get_list(data, "pace_zones", "paceZones"),
            power_zone_names=_str_list(data, "power_zone_names", "powerZoneNames"),
            hr_zone_names=_str_list(data, "hr_zone_names", "hrZoneNames"),
            pace_zone_names=_str_list(data, "pace_zone_names", "paceZoneNames"),
            custom_zones_ids=[
                v
                for v in _get_list(data, "custom_zones_ids", "customZonesIds")
                if isinstance(v, int) and not isinstance(v, bool)
            ],
            warmup_time=_first(data.get("warmup_time"), data.get("warmup")),
            cooldown_time=_first(data.get("cooldown_time"), data.get("cooldown")),
        )
```

Add this helper next to the other module-level helpers (after `_get_list`, around line 31):

```python
def _str_list(data: dict[str, Any], *keys: str) -> list[str]:
    """Get the first list value found for the given keys as a list of strings."""
    return [str(v) for v in _get_list(data, *keys) if v is not None]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py tests/test_formatting.py tests/test_server.py -q`

Expected: PASS. The existing `test_format_sport_settings` still passes because `types` is empty for
a directly-constructed object, so `type` remains the source of the label.

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff check . && uv run mypy src tests
git add src/intervals_mcp_server/utils/schemas.py tests/test_schemas.py
git commit -m "fix: parse sport settings types array instead of missing type key

The API returns types: [\"Run\", \"VirtualRun\", \"TrailRun\"], not a scalar
type, so every sport rendered as \"Sport: N/A\". Also adds the zone name
lists and custom_zones_ids needed for custom zone support."
```

---

### Task 2: `CustomZone` and `CustomZoneSet` schemas

**Files:**
- Modify: `src/intervals_mcp_server/utils/schemas.py` (add after the `CustomItem` dataclass, around line 758)
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: the `CustomItemType` enum (line 108) and the `field` import already present.
- Produces:
  - `CustomZone(id, name, start, end, color, start_anchor, end_anchor)` with a `code` property
    returning `"CZ" + id` (e.g. `"CZZ2"`) or `None` when `id` is missing.
  - `CustomZoneSet(item_id, name, code, anchor, stream_type, round_zones_down, use_pace_units, zones)`
    with `CustomZoneSet.from_custom_item(data: dict) -> CustomZoneSet | None`.
  - `_as_float(value) -> float | None` module helper.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_schemas.py` (add `CustomZone, CustomZoneSet` to the existing import from
`intervals_mcp_server.utils.schemas`):

```python
# ── CustomZoneSet ─────────────────────────────────────────────────────────

ZONES_ITEM = {
    "id": 945743,
    "type": "ZONES",
    "name": "8020 endurance",
    "content": {
        "code": "Endurance8020",
        "anchor": "lthr",
        "stream_type": "heartrate",
        "round_zones_down": True,
        "use_pace_units": False,
        "zones": [
            {"id": "Z1", "name": "Zone 1", "start": 0.72, "end": 0.81, "color": "#aaa",
             "start_anchor": "", "end_anchor": ""},
            {"id": "Z2", "name": "Zone 2", "start": 0.81, "end": 0.90, "color": "#bbb",
             "start_anchor": "", "end_anchor": ""},
        ],
    },
}


def test_custom_zone_set_from_custom_item():
    """from_custom_item() reads the ZONES content block into a typed set."""
    zs = CustomZoneSet.from_custom_item(ZONES_ITEM)
    assert zs is not None
    assert zs.item_id == 945743
    assert zs.name == "8020 endurance"
    assert zs.code == "Endurance8020"
    assert zs.anchor == "lthr"
    assert zs.stream_type == "heartrate"
    assert zs.round_zones_down is True
    assert len(zs.zones) == 2
    assert zs.zones[1].start == 0.81
    assert zs.zones[1].end == 0.90


def test_custom_zone_code_is_cz_plus_id():
    """The workout-text code is 'CZ' + the zone id, so 'Z2' becomes 'CZZ2'."""
    zs = CustomZoneSet.from_custom_item(ZONES_ITEM)
    assert zs is not None
    assert [z.code for z in zs.zones] == ["CZZ1", "CZZ2"]


def test_custom_zone_empty_anchor_string_becomes_none():
    """The API sends '' for absent per-zone anchors; normalise those to None."""
    zs = CustomZoneSet.from_custom_item(ZONES_ITEM)
    assert zs is not None
    assert zs.zones[0].start_anchor is None
    assert zs.zones[0].end_anchor is None


def test_custom_zone_set_keeps_per_zone_anchor_override():
    """A non-empty per-zone anchor is preserved for the resolver to use."""
    item = {
        "id": 1012352,
        "type": "ZONES",
        "name": "80/20 Potencia",
        "content": {
            "anchor": "ftp",
            "stream_type": "watts",
            "zones": [{"id": "Z5", "name": "Neuromuscular", "start": 1.2, "end": 2.0,
                       "start_anchor": "ftp", "end_anchor": ""}],
        },
    }
    zs = CustomZoneSet.from_custom_item(item)
    assert zs is not None
    assert zs.zones[0].start_anchor == "ftp"
    assert zs.zones[0].end_anchor is None


def test_custom_zone_set_rejects_non_zones_item():
    """Items of another type are not zone sets."""
    assert CustomZoneSet.from_custom_item({"id": 1, "type": "FITNESS_CHART", "content": {}}) is None


def test_custom_zone_set_rejects_malformed_content():
    """Missing or non-list zones means the item is unusable."""
    assert CustomZoneSet.from_custom_item({"id": 1, "type": "ZONES"}) is None
    assert CustomZoneSet.from_custom_item({"id": 1, "type": "ZONES", "content": {}}) is None
    assert CustomZoneSet.from_custom_item(
        {"id": 1, "type": "ZONES", "content": {"zones": "nope"}}
    ) is None


def test_custom_zone_set_skips_non_dict_zones():
    """Junk entries inside zones are dropped, not fatal."""
    zs = CustomZoneSet.from_custom_item(
        {"id": 1, "type": "ZONES", "content": {"zones": [{"id": "Z1"}, "junk", None]}}
    )
    assert zs is not None
    assert len(zs.zones) == 1


def test_custom_zone_set_defaults_round_down_true():
    """round_zones_down defaults to True, matching Intervals.icu's default."""
    zs = CustomZoneSet.from_custom_item({"id": 1, "type": "ZONES", "content": {"zones": []}})
    assert zs is not None
    assert zs.round_zones_down is True
    assert zs.use_pace_units is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_schemas.py -k custom_zone -v`

Expected: FAIL at import with `ImportError: cannot import name 'CustomZoneSet'`.

- [ ] **Step 3: Implement**

Add `_as_float` next to the other module helpers in `schemas.py` (after `_str_list` from Task 1):

```python
def _as_float(value: Any) -> float | None:
    """Coerce a numeric value to float, returning None for non-numeric input."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

Add both dataclasses after `CustomItem`:

```python
@dataclass
class CustomZone:
    """One band of a custom zone set, stored as a fraction of an anchor threshold."""

    id: str | None = None
    name: str | None = None
    start: float | None = None
    end: float | None = None
    color: str | None = None
    start_anchor: str | None = None
    end_anchor: str | None = None

    @property
    def code(self) -> str | None:
        """The workout-text code for this zone — 'CZ' + the zone id, e.g. 'CZZ2'."""
        return f"CZ{self.id}" if self.id else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomZone":
        """Create a CustomZone from a raw zone dict inside a ZONES item's content."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            start=_as_float(data.get("start")),
            end=_as_float(data.get("end")),
            color=data.get("color"),
            start_anchor=data.get("start_anchor") or None,
            end_anchor=data.get("end_anchor") or None,
        )


@dataclass
class CustomZoneSet:
    """A custom zone set — a custom item of type ZONES, linked from sport settings."""

    item_id: int | None = None
    name: str | None = None
    code: str | None = None
    anchor: str | None = None
    stream_type: str | None = None
    round_zones_down: bool = True
    use_pace_units: bool = False
    zones: list[CustomZone] = field(default_factory=list)

    @classmethod
    def from_custom_item(cls, data: dict[str, Any]) -> "CustomZoneSet | None":
        """Create a CustomZoneSet from a raw custom-item dict, or None if it is not a usable ZONES item."""
        if not isinstance(data, dict) or data.get("type") != CustomItemType.ZONES:
            return None
        content = data.get("content")
        if not isinstance(content, dict):
            return None
        raw_zones = content.get("zones")
        if not isinstance(raw_zones, list):
            return None
        return cls(
            item_id=data.get("id"),
            name=data.get("name"),
            code=content.get("code"),
            anchor=content.get("anchor"),
            stream_type=content.get("stream_type"),
            round_zones_down=bool(content.get("round_zones_down", True)),
            use_pace_units=bool(content.get("use_pace_units", False)),
            zones=[CustomZone.from_dict(z) for z in raw_zones if isinstance(z, dict)],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas.py -k custom_zone -v`

Expected: PASS (8 tests).

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff check . && uv run mypy src tests && uv run pytest -q
git add src/intervals_mcp_server/utils/schemas.py tests/test_schemas.py
git commit -m "feat: add CustomZone and CustomZoneSet schemas

Custom zone sets are custom items of type ZONES whose content holds
zone bands as fractions of an anchor threshold. The workout-text code
for a zone is \"CZ\" + the zone id."
```

---

### Task 3: Pure zone resolver (`utils/zones.py`)

**Files:**
- Create: `src/intervals_mcp_server/utils/zones.py`
- Test: `tests/test_zones.py`

**Interfaces:**
- Consumes: `CustomZone`, `CustomZoneSet` from Task 2.
- Produces:
  - `ResolvedZone(code, name, start_pct, end_pct, start_value, end_value, unit, note)` —
    `start_pct`/`end_pct` are `float | None` percentages (81.0, not 0.81); `start_value`/`end_value`
    are `int | None`; `unit` is `str` (`"bpm"`, `"W"`, or `""`); `note` is `str | None`.
  - `resolve_zone_set(zone_set: CustomZoneSet, lthr: int | None, ftp: int | None) -> list[ResolvedZone]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_zones.py`:

```python
"""
Unit tests for custom zone resolution.

resolve_zone_set() is pure — it turns fractional zone bands into concrete heart rates or
watts using the sport's LTHR/FTP. The expected values below were verified against a real
Intervals.icu account.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.utils.schemas import CustomZoneSet  # noqa: E402
from intervals_mcp_server.utils.zones import resolve_zone_set  # noqa: E402


def _hr_zone_set(**content_overrides):
    """Build the real '8020 endurance' HR zone set, with optional content overrides."""
    content = {
        "code": "Endurance8020",
        "anchor": "lthr",
        "stream_type": "heartrate",
        "round_zones_down": True,
        "use_pace_units": False,
        "zones": [
            {"id": "Z1", "name": "Zone 1", "start": 0.72, "end": 0.81},
            {"id": "Z2", "name": "Zone 2", "start": 0.81, "end": 0.90},
        ],
    }
    content.update(content_overrides)
    zs = CustomZoneSet.from_custom_item(
        {"id": 945743, "type": "ZONES", "name": "8020 endurance", "content": content}
    )
    assert zs is not None
    return zs


def test_resolve_czz2_at_lthr_170():
    """Verified against the live account: CZZ2 is 137-153 bpm at LTHR 170."""
    resolved = resolve_zone_set(_hr_zone_set(), lthr=170, ftp=None)
    czz2 = next(z for z in resolved if z.code == "CZZ2")
    assert (czz2.start_value, czz2.end_value) == (137, 153)
    assert czz2.unit == "bpm"
    assert czz2.note is None


def test_resolve_czz2_at_lthr_165():
    """Verified against the live account: CZZ2 is 133-148 bpm at LTHR 165."""
    resolved = resolve_zone_set(_hr_zone_set(), lthr=165, ftp=None)
    czz2 = next(z for z in resolved if z.code == "CZZ2")
    assert (czz2.start_value, czz2.end_value) == (133, 148)


def test_resolve_exposes_percentages():
    """Fractions are surfaced as percentages so the model can show the band definition."""
    resolved = resolve_zone_set(_hr_zone_set(), lthr=170, ftp=None)
    assert (resolved[0].start_pct, resolved[0].end_pct) == (72.0, 81.0)
    assert resolved[0].name == "Zone 1"


def test_round_zones_down_false_rounds_to_nearest():
    """With round_zones_down false, 0.81 x 170 = 137.7 rounds up to 138 instead of flooring."""
    resolved = resolve_zone_set(_hr_zone_set(round_zones_down=False), lthr=170, ftp=None)
    czz2 = next(z for z in resolved if z.code == "CZZ2")
    assert czz2.start_value == 138
    assert czz2.end_value == 153


def test_per_zone_anchor_override_uses_other_threshold():
    """A per-zone start_anchor overrides the set anchor for that boundary only."""
    zs = _hr_zone_set(
        zones=[{"id": "Z5", "name": "Zone 5", "start": 1.05, "end": 1.3, "start_anchor": "ftp"}]
    )
    resolved = resolve_zone_set(zs, lthr=170, ftp=250)
    assert resolved[0].start_value == 262  # floor(1.05 * 250), from the ftp override
    assert resolved[0].end_value == 221    # floor(1.30 * 170), from the set anchor


def test_missing_anchor_threshold_yields_note_not_guess():
    """With no LTHR there is nothing to resolve against; report it rather than guessing."""
    resolved = resolve_zone_set(_hr_zone_set(), lthr=None, ftp=250)
    czz2 = next(z for z in resolved if z.code == "CZZ2")
    assert czz2.start_value is None
    assert czz2.end_value is None
    assert czz2.start_pct == 81.0
    assert czz2.note is not None
    assert "LTHR" in czz2.note


def test_zero_threshold_treated_as_missing():
    """A zero threshold is not a usable anchor."""
    resolved = resolve_zone_set(_hr_zone_set(), lthr=0, ftp=None)
    assert resolved[0].start_value is None
    assert resolved[0].note is not None


def test_unrecognised_anchor_yields_note():
    """An anchor name the server does not understand is reported, not raised."""
    resolved = resolve_zone_set(_hr_zone_set(anchor="pace"), lthr=170, ftp=250)
    assert resolved[0].start_value is None
    assert resolved[0].note is not None
    assert "pace" in resolved[0].note


def test_watts_zone_set_uses_watt_unit():
    """An FTP-anchored set resolves against FTP and reports watts."""
    zs = _hr_zone_set(
        anchor="ftp",
        stream_type="watts",
        zones=[{"id": "Z2", "name": "Endurance", "start": 0.76, "end": 0.88}],
    )
    resolved = resolve_zone_set(zs, lthr=170, ftp=250)
    assert (resolved[0].start_value, resolved[0].end_value) == (190, 220)
    assert resolved[0].unit == "W"


def test_empty_zone_set_resolves_to_empty_list():
    """A set with no zones is not an error."""
    assert resolve_zone_set(_hr_zone_set(zones=[]), lthr=170, ftp=None) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_zones.py -v`

Expected: FAIL at collection with `ModuleNotFoundError: No module named 'intervals_mcp_server.utils.zones'`.

- [ ] **Step 3: Implement**

Create `src/intervals_mcp_server/utils/zones.py`:

```python
"""
Custom zone resolution for Intervals.icu.

Custom zone sets store their bands as fractions of an anchor threshold (LTHR or FTP).
This module turns those fractions into concrete heart rates or watts. It is pure — no I/O,
no API calls — so the arithmetic can be tested directly.
"""

import math
from dataclasses import dataclass

from intervals_mcp_server.utils.schemas import CustomZoneSet

ANCHOR_LTHR = "lthr"
ANCHOR_FTP = "ftp"

_UNIT_BY_STREAM = {"heartrate": "bpm", "watts": "W"}


@dataclass
class ResolvedZone:
    """A custom zone with its fractional bounds resolved to concrete values where possible."""

    code: str
    name: str
    start_pct: float | None
    end_pct: float | None
    start_value: int | None
    end_value: int | None
    unit: str
    note: str | None = None


def _anchor_value(
    anchor: str | None, lthr: int | None, ftp: int | None
) -> tuple[int | None, str | None]:
    """Resolve an anchor name to its threshold value, plus a note when it cannot be resolved."""
    if anchor == ANCHOR_LTHR:
        return (lthr, None) if lthr else (None, "LTHR is not set for this sport.")
    if anchor == ANCHOR_FTP:
        return (ftp, None) if ftp else (None, "FTP is not set for this sport.")
    if not anchor:
        return None, "Zone set has no anchor threshold."
    return None, f"Unrecognised anchor {anchor!r}; cannot resolve to a value."


def resolve_zone_set(
    zone_set: CustomZoneSet,
    lthr: int | None,
    ftp: int | None,
) -> list[ResolvedZone]:
    """Resolve each zone's fractional bounds against the sport's LTHR and FTP.

    Per-zone start_anchor/end_anchor override the set's anchor for that boundary. Bounds are
    floored when round_zones_down is set (the Intervals.icu default) and rounded otherwise.
    A bound with no usable anchor stays None and carries a note rather than a guessed value.
    """

    def _round(value: float) -> int:
        return math.floor(value) if zone_set.round_zones_down else round(value)

    unit = _UNIT_BY_STREAM.get(zone_set.stream_type or "", "")
    resolved: list[ResolvedZone] = []

    for zone in zone_set.zones:
        notes: list[str] = []
        bounds: list[int | None] = []
        for fraction, override in ((zone.start, zone.start_anchor), (zone.end, zone.end_anchor)):
            value, note = _anchor_value(override or zone_set.anchor, lthr, ftp)
            if note and note not in notes:
                notes.append(note)
            bounds.append(None if fraction is None or value is None else _round(fraction * value))

        resolved.append(
            ResolvedZone(
                code=zone.code or "",
                name=zone.name or "",
                start_pct=None if zone.start is None else zone.start * 100,
                end_pct=None if zone.end is None else zone.end * 100,
                start_value=bounds[0],
                end_value=bounds[1],
                unit=unit,
                note=" ".join(notes) or None,
            )
        )

    return resolved
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_zones.py -v`

Expected: PASS (10 tests).

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff check . && uv run mypy src tests
git add src/intervals_mcp_server/utils/zones.py tests/test_zones.py
git commit -m "feat: resolve custom zone fractions to bpm and watts

Zone bands are fractions of LTHR or FTP. resolve_zone_set() applies the
set's anchor (with per-zone overrides) and rounding mode. Verified
against the live account: CZZ2 of the 8020 endurance set is 137-153 bpm
at LTHR 170 and 133-148 at 165."
```

---

### Task 4: Zone-set formatters

**Files:**
- Modify: `src/intervals_mcp_server/utils/formatting.py`
- Test: `tests/test_formatting.py`

**Interfaces:**
- Consumes: `CustomZoneSet` (Task 2), `ResolvedZone` and `resolve_zone_set` (Task 3), and the
  existing module-private `_fmt` helper.
- Produces:
  - `format_custom_zone_set(zone_set: CustomZoneSet, resolved: list[ResolvedZone]) -> str`
  - `format_unattached_zone_set(zone_set: CustomZoneSet) -> str`

Note: the spec sketched the unattached section as pipe-separated; this plan renders one zone per
line instead. Same information, easier to read, consistent with the attached table.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_formatting.py` (add `format_custom_zone_set, format_unattached_zone_set` to
the import from `intervals_mcp_server.utils.formatting`, `CustomZoneSet` to the import from
`intervals_mcp_server.utils.schemas`, and `from intervals_mcp_server.utils.zones import resolve_zone_set`):

```python
# ── custom zone formatting tests ─────────────────────────────────────────

_ZONES_ITEM = {
    "id": 945743,
    "type": "ZONES",
    "name": "8020 endurance",
    "content": {
        "code": "Endurance8020",
        "anchor": "lthr",
        "stream_type": "heartrate",
        "round_zones_down": True,
        "zones": [
            {"id": "Z1", "name": "Zone 1", "start": 0.72, "end": 0.81},
            {"id": "Z2", "name": "Zone 2", "start": 0.81, "end": 0.90},
        ],
    },
}


def test_format_custom_zone_set_renders_codes_and_values():
    """The table shows each CZ code with its percentage band and resolved bpm."""
    zs = CustomZoneSet.from_custom_item(_ZONES_ITEM)
    assert zs is not None
    result = format_custom_zone_set(zs, resolve_zone_set(zs, lthr=170, ftp=None))
    assert "8020 endurance" in result
    assert "945743" in result
    assert "bpm" in result
    assert "CZZ2" in result
    assert "81-90%" in result
    assert "137-153" in result


def test_format_custom_zone_set_shows_note_when_unresolvable():
    """Without LTHR the values are dashed out and the reason is stated."""
    zs = CustomZoneSet.from_custom_item(_ZONES_ITEM)
    assert zs is not None
    result = format_custom_zone_set(zs, resolve_zone_set(zs, lthr=None, ftp=None))
    assert "81-90%" in result
    assert "137-153" not in result
    assert "LTHR is not set" in result


def test_format_custom_zone_set_handles_empty_zones():
    """A set with no zones renders a message rather than an empty table."""
    zs = CustomZoneSet.from_custom_item({"id": 5, "type": "ZONES", "name": "Empty",
                                        "content": {"zones": []}})
    assert zs is not None
    result = format_custom_zone_set(zs, [])
    assert "no zones defined" in result


def test_format_unattached_zone_set_shows_fractions_only():
    """An unattached set has no threshold to resolve against, so only percentages are shown."""
    zs = CustomZoneSet.from_custom_item({
        "id": 1012352,
        "type": "ZONES",
        "name": "80/20 Potencia",
        "content": {
            "anchor": "ftp",
            "stream_type": "watts",
            "zones": [{"id": "Z2", "name": "Endurance", "start": 0.76, "end": 0.88}],
        },
    })
    assert zs is not None
    result = format_unattached_zone_set(zs)
    assert "80/20 Potencia" in result
    assert "anchor: ftp" in result
    assert "CZZ2" in result
    assert "76-88%" in result
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_formatting.py -k custom_zone -v`

Expected: FAIL at import with `ImportError: cannot import name 'format_custom_zone_set'`.

- [ ] **Step 3: Implement**

In `formatting.py`, add `CustomZoneSet` to the existing import from `utils.schemas` and add a new
import for the resolver's dataclass:

```python
from intervals_mcp_server.utils.zones import ResolvedZone
```

Append these functions after `format_sport_settings`:

```python
def _trim_pct(value: float) -> str:
    """Render a percentage without float noise or trailing zeros (90.0 -> '90')."""
    return f"{value:.10g}"


def _pct_range(start: float | None, end: float | None) -> str:
    """Format a zone's percentage band, e.g. '81-90%'."""
    if start is None or end is None:
        return "N/A"
    return f"{_trim_pct(start)}-{_trim_pct(end)}%"


def _value_range(start: int | None, end: int | None) -> str:
    """Format a resolved zone band, or a dash when the anchor threshold is unknown."""
    if start is None or end is None:
        return "-"
    return f"{start}-{end}"


def _zone_set_header(zone_set: CustomZoneSet) -> str:
    """Format the identifying line for a zone set."""
    parts = []
    if zone_set.stream_type:
        parts.append(str(zone_set.stream_type))
    if zone_set.anchor:
        parts.append(f"anchor: {zone_set.anchor}")
    suffix = f", {', '.join(parts)}" if parts else ""
    return f"Set: {_fmt(zone_set.name)}  [id {_fmt(zone_set.item_id)}{suffix}]"


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> list[str]:
    """Render fixed-width columns, indented two spaces."""
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    return [
        "  " + "  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip()
        for row in [headers, *rows]
    ]


def format_custom_zone_set(zone_set: CustomZoneSet, resolved: list[ResolvedZone]) -> str:
    """Format a resolved custom zone set as a code/name/range/value table."""
    lines = [_zone_set_header(zone_set), ""]
    if not resolved:
        lines.append("  (no zones defined)")
        return "\n".join(lines)

    unit = next((z.unit for z in resolved if z.unit), "Value")
    rows = [
        (
            z.code,
            z.name,
            _pct_range(z.start_pct, z.end_pct),
            _value_range(z.start_value, z.end_value),
        )
        for z in resolved
    ]
    lines.extend(_table(("Code", "Name", "Range", unit), rows))

    notes = sorted({z.note for z in resolved if z.note})
    if notes:
        lines.append("")
        lines.extend(f"  Note: {note}" for note in notes)
    return "\n".join(lines)


def format_unattached_zone_set(zone_set: CustomZoneSet) -> str:
    """Format a zone set no sport links to — percentages only, with no threshold to resolve against."""
    lines = [_zone_set_header(zone_set)]
    if not zone_set.zones:
        lines.append("  (no zones defined)")
        return "\n".join(lines)
    rows = [
        (
            zone.code or "",
            zone.name or "",
            _pct_range(
                None if zone.start is None else zone.start * 100,
                None if zone.end is None else zone.end * 100,
            ),
        )
        for zone in zone_set.zones
    ]
    lines.extend(_table(("Code", "Name", "Range"), rows))
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_formatting.py -v`

Expected: PASS, including the pre-existing formatting tests.

- [ ] **Step 5: Lint, type check, commit**

```bash
uv run ruff check . && uv run mypy src tests
git add src/intervals_mcp_server/utils/formatting.py tests/test_formatting.py
git commit -m "feat: format custom zone sets as CZ code tables"
```

---

### Task 5: `get_custom_zones` tool and registration

**Files:**
- Modify: `src/intervals_mcp_server/tools/athlete.py`
- Modify: `src/intervals_mcp_server/tools/__init__.py` (import line 32, `__all__` around line 75)
- Modify: `src/intervals_mcp_server/server.py` (docstring list around line 43, import around line 111, `__all__` around line 154)
- Modify: `tests/sample_data.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `AthleteSportSettings` (Task 1), `CustomZoneSet` (Task 2), `resolve_zone_set` (Task 3),
  `format_custom_zone_set` / `format_unattached_zone_set` (Task 4), and the existing
  `make_intervals_request` and `resolve_athlete_id`.
- Produces:
  - `get_custom_zones(sport_type=None, athlete_id=None, api_key=None) -> str` MCP tool.
  - Module-private `_parse_sport_groups(result) -> list[AthleteSportSettings]`,
    `_parse_zone_sets(result) -> dict[int, CustomZoneSet]`, and
    `_matches_sport(group, sport_type) -> bool`, reused by Task 6.

- [ ] **Step 1: Add fixtures**

Append to `tests/sample_data.py`:

```python
# Sport settings in the shape the live API returns: a `types` array plus custom_zones_ids.
SPORT_SETTINGS_WITH_ZONES = [
    {
        "types": ["Run", "VirtualRun", "TrailRun"],
        "lthr": 170,
        "ftp": None,
        "maxHr": 189,
        "hr_zones": [122, 137, 153, 161, 170, 173, 189],
        "hr_zone_names": ["Z1", "Z2", "ZX", "Z3", "ZY", "Z4", "Z5"],
        "custom_zones_ids": [945743],
        "warmup": 300,
        "cooldown": 300,
    },
    {
        "types": ["Ride", "GravelRide"],
        "lthr": 165,
        "ftp": None,
        "maxHr": 189,
        "custom_zones_ids": [],
        "warmup": 600,
        "cooldown": 300,
    },
]

CUSTOM_ITEMS_WITH_ZONES = [
    {
        "id": 451100,
        "type": "FITNESS_CHART",
        "name": "Weight",
        "content": {},
    },
    {
        "id": 945743,
        "type": "ZONES",
        "name": "8020 endurance",
        "content": {
            "code": "Endurance8020",
            "anchor": "lthr",
            "stream_type": "heartrate",
            "round_zones_down": True,
            "use_pace_units": False,
            "zones": [
                {"id": "Z1", "name": "Zone 1", "start": 0.72, "end": 0.81},
                {"id": "Z2", "name": "Zone 2", "start": 0.81, "end": 0.90},
                {"id": "Z5", "name": "Zone 5", "start": 1.05, "end": 1.30},
            ],
        },
    },
    {
        "id": 1012352,
        "type": "ZONES",
        "name": "80/20 Potencia",
        "content": {
            "code": "Potencia8020",
            "anchor": "ftp",
            "stream_type": "watts",
            "round_zones_down": True,
            "zones": [{"id": "Z2", "name": "Endurance", "start": 0.76, "end": 0.88}],
        },
    },
]
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_server.py` (add `get_custom_zones` to the import from
`intervals_mcp_server.server`, and `CUSTOM_ITEMS_WITH_ZONES, SPORT_SETTINGS_WITH_ZONES` to the
import from `tests.sample_data`):

```python
def _patch_zone_endpoints(monkeypatch, settings=None, items=None):
    """Route sport-settings and custom-item requests to separate fixtures.

    get_custom_zones calls two endpoints, so the fake must dispatch on the URL rather
    than return one payload for everything.
    """
    settings = SPORT_SETTINGS_WITH_ZONES if settings is None else settings
    items = CUSTOM_ITEMS_WITH_ZONES if items is None else items

    async def fake_request(url, *_args, **_kwargs):
        if "sport-settings" in url:
            return settings
        if "custom-item" in url:
            return items
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)


def test_get_custom_zones_resolves_codes_to_bpm(monkeypatch):
    """CZ codes resolve against the sport's LTHR — CZZ2 is 137-153 bpm at LTHR 170."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(sport_type="Run", athlete_id="i1"))
    assert "Run" in result
    assert "8020 endurance" in result
    assert "CZZ2" in result
    assert "137-153" in result
    assert "bpm" in result


def test_get_custom_zones_matches_sport_alias(monkeypatch):
    """TrailRun selects the Run settings group, case-insensitively."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(sport_type="trailrun", athlete_id="i1"))
    assert "CZZ2" in result
    assert "137-153" in result


def test_get_custom_zones_unknown_sport(monkeypatch):
    """An unmatched sport type is reported rather than silently returning everything."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(sport_type="Kayaking", athlete_id="i1"))
    assert "Kayaking" in result
    assert "CZZ2" not in result


def test_get_custom_zones_reports_sport_without_custom_zones(monkeypatch):
    """A sport with an empty custom_zones_ids says so instead of being omitted."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(sport_type="Ride", athlete_id="i1"))
    assert "none configured" in result


def test_get_custom_zones_lists_unattached_sets(monkeypatch):
    """A ZONES item no sport links to is listed separately, with percentages only."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(athlete_id="i1"))
    assert "Not attached to any sport" in result
    assert "80/20 Potencia" in result
    assert "76-88%" in result


def test_get_custom_zones_omits_unattached_when_sport_given(monkeypatch):
    """Asking about one sport should not drag in unrelated zone sets."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_custom_zones(sport_type="Run", athlete_id="i1"))
    assert "Not attached to any sport" not in result


def test_get_custom_zones_custom_item_error(monkeypatch):
    """A failed custom-item fetch surfaces the API error message."""
    async def fake_request(url, *_args, **_kwargs):
        if "sport-settings" in url:
            return SPORT_SETTINGS_WITH_ZONES
        return {"error": True, "message": "Rate limited"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_custom_zones(athlete_id="i1"))
    assert "Error fetching custom items" in result
    assert "Rate limited" in result


def test_get_custom_zones_sport_settings_error(monkeypatch):
    """A failed sport-settings fetch surfaces the API error message."""
    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_custom_zones(athlete_id="i1"))
    assert "Error fetching sport settings" in result


def test_get_custom_zones_skips_malformed_zone_set(monkeypatch):
    """A ZONES item with junk content is skipped; the good set still renders."""
    items = [{"id": 999, "type": "ZONES", "name": "Broken", "content": {"zones": "nope"}}]
    items.extend(CUSTOM_ITEMS_WITH_ZONES)
    _patch_zone_endpoints(monkeypatch, items=items)
    result = asyncio.run(get_custom_zones(sport_type="Run", athlete_id="i1"))
    assert "CZZ2" in result
    assert "Broken" not in result
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest tests/test_server.py -k custom_zones -v`

Expected: FAIL at import with `ImportError: cannot import name 'get_custom_zones'`.

- [ ] **Step 4: Implement the tool**

In `src/intervals_mcp_server/tools/athlete.py`, extend the imports:

```python
from intervals_mcp_server.utils.formatting import (
    format_athlete_summary,
    format_custom_zone_set,
    format_sport_settings,
    format_training_plan,
    format_unattached_zone_set,
)
from intervals_mcp_server.utils.schemas import (
    Athlete,
    AthleteSportSettings,
    AthleteTrainingPlan,
    CustomZoneSet,
)
from intervals_mcp_server.utils.zones import resolve_zone_set
```

Add the private helpers after the `logger`/`config` lines:

```python
def _parse_sport_groups(result: Any) -> list[AthleteSportSettings]:
    """Parse a sport-settings response into settings objects, skipping unparseable entries."""
    items = (
        result
        if isinstance(result, list)
        else list(result.values()) if isinstance(result, dict) else []
    )
    groups: list[AthleteSportSettings] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            groups.append(AthleteSportSettings.from_dict(item))
        except (TypeError, KeyError, ValueError) as e:
            logger.error("Failed to parse sport settings entry: %s", e, exc_info=True)
    return groups


def _parse_zone_sets(result: Any) -> dict[int, CustomZoneSet]:
    """Parse a custom-item response into usable ZONES sets, keyed by custom item id."""
    sets: dict[int, CustomZoneSet] = {}
    for item in result if isinstance(result, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            zone_set = CustomZoneSet.from_custom_item(item)
        except (TypeError, KeyError, ValueError) as e:
            logger.error(
                "Failed to parse custom zone set %r: %s", item.get("id"), e, exc_info=True
            )
            continue
        if zone_set is not None and zone_set.item_id is not None:
            sets[zone_set.item_id] = zone_set
    return sets


def _matches_sport(group: AthleteSportSettings, sport_type: str | None) -> bool:
    """Check whether a settings group covers the given sport type, case-insensitively."""
    if sport_type is None:
        return True
    names = [t.casefold() for t in group.types]
    if group.type:
        names.append(str(group.type).casefold())
    return sport_type.strip().casefold() in names
```

Add the tool after `get_sport_settings`:

```python
@mcp.tool()
async def get_custom_zones(
    sport_type: str | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """Get custom training zones (CZ codes) with their resolved heart rates or watts.

    Intervals.icu workout text references custom zones as "CZ" + the zone id, e.g. "- 10m CZZ2 HR".
    Their bands are stored as fractions of the sport's LTHR or FTP; this tool resolves them to
    concrete values. The standard HR zones returned by get_sport_settings are a different zone
    model and must not be mapped onto CZ codes.

    Args:
        sport_type: Optional sport to report on (e.g. 'Run', 'TrailRun', 'Ride'). Matches any sport
            within a settings group. Omitted, every sport is reported plus any unattached zone sets.
        athlete_id: Do not provide — the server uses the pre-configured ATHLETE_ID automatically.
        api_key: The Intervals.icu API key (optional, uses API_KEY from env if not provided).
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    settings_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/sport-settings", api_key=api_key
    )
    if isinstance(settings_result, dict) and settings_result.get("error"):
        return f"Error fetching sport settings: {settings_result.get('message', 'Unknown error')}"

    items_result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/custom-item", api_key=api_key
    )
    if isinstance(items_result, dict) and items_result.get("error"):
        return f"Error fetching custom items: {items_result.get('message', 'Unknown error')}"

    groups = _parse_sport_groups(settings_result)
    zone_sets = _parse_zone_sets(items_result)

    matched = [g for g in groups if _matches_sport(g, sport_type)]
    if sport_type and not matched:
        return f"No sport settings found for sport type '{sport_type}'."

    blocks: list[str] = []
    for group in matched:
        label = ", ".join(group.types) or _fmt_sport(group)
        linked = [zone_sets[i] for i in group.custom_zones_ids if i in zone_sets]
        if not linked:
            blocks.append(f"Custom zones for {label}: none configured.")
            continue
        parts = [f"Custom zones for {label} (LTHR {group.lthr}, FTP {group.ftp})"]
        parts.extend(
            format_custom_zone_set(zs, resolve_zone_set(zs, group.lthr, group.ftp))
            for zs in linked
        )
        blocks.append("\n".join(parts))

    if sport_type is None:
        attached = {i for g in groups for i in g.custom_zones_ids}
        unattached = [zs for item_id, zs in zone_sets.items() if item_id not in attached]
        if unattached:
            parts = ["Not attached to any sport (no threshold to resolve against)"]
            parts.extend(format_unattached_zone_set(zs) for zs in unattached)
            blocks.append("\n".join(parts))

    if not blocks:
        return "No sport settings found."

    blocks.append('Use these codes in workout text, e.g. "- 10m CZZ2 HR".')
    return "\n\n".join(blocks)
```

Add this small helper next to the other private helpers:

```python
def _fmt_sport(group: AthleteSportSettings) -> str:
    """Label a settings group that has no `types` array."""
    return str(group.type) if group.type else "Unknown sport"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_server.py -k custom_zones -v`

Expected: PASS (9 tests).

- [ ] **Step 6: Register the tool**

In `src/intervals_mcp_server/tools/__init__.py`, change the athlete import to:

```python
from intervals_mcp_server.tools.athlete import get_athlete, get_custom_zones, get_sport_settings
```

and add `"get_custom_zones",` to `__all__` immediately after `"get_sport_settings",`.

In `src/intervals_mcp_server/server.py`:
- add `        - get_custom_zones` to the module docstring list, after `        - get_sport_settings`;
- add `    get_custom_zones,` to the `from intervals_mcp_server.tools.athlete import (...)` block
  (keep the block alphabetical: `get_athlete, get_custom_zones, get_sport_settings, get_training_plan, update_sport_settings`);
- add `    "get_custom_zones",` to `__all__` after `"get_sport_settings",`.

- [ ] **Step 7: Verify registration and full suite**

```bash
uv run python -c "from intervals_mcp_server.server import get_custom_zones; print(get_custom_zones.name)"
uv run pytest -q && uv run ruff check . && uv run mypy src tests
```

Expected: prints `get_custom_zones`, then all checks pass.

- [ ] **Step 8: Commit**

```bash
git add src/intervals_mcp_server/tools/athlete.py src/intervals_mcp_server/tools/__init__.py \
        src/intervals_mcp_server/server.py tests/test_server.py tests/sample_data.py
git commit -m "feat: add get_custom_zones tool

Joins sport settings to ZONES custom items via custom_zones_ids and
resolves each zone's fractional band to bpm or watts, so CZ codes used
in workout text can be checked against real thresholds."
```

---

### Task 6: Enrich `get_sport_settings`

**Files:**
- Modify: `src/intervals_mcp_server/utils/formatting.py` (`format_sport_settings`, around line 494)
- Modify: `src/intervals_mcp_server/tools/athlete.py` (`get_sport_settings`, around line 60)
- Test: `tests/test_formatting.py`, `tests/test_server.py`

**Interfaces:**
- Consumes: `_parse_sport_groups`, `_parse_zone_sets` (Task 5); `AthleteSportSettings` fields from Task 1.
- Produces: `format_sport_settings(setting, zone_set_names: dict[int, str] | None = None) -> str`.
  The second parameter is optional, so all existing call sites keep working.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_formatting.py`:

```python
def test_format_sport_settings_labels_zone_boundaries():
    """Zone names supplied by the API are paired with their boundary values."""
    s = AthleteSportSettings(
        types=["Run", "TrailRun"],
        lthr=170,
        hr_zones=[137, 153, 170],
        hr_zone_names=["Easy", "Tempo", "Threshold"],
    )
    result = format_sport_settings(s)
    assert "Sport: Run, TrailRun" in result
    assert "Easy 137" in result
    assert "Threshold 170" in result


def test_format_sport_settings_points_at_custom_zones():
    """A linked custom zone set is named, with a pointer to the tool that resolves it."""
    s = AthleteSportSettings(types=["Run"], lthr=170, custom_zones_ids=[945743])
    result = format_sport_settings(s, zone_set_names={945743: "8020 endurance"})
    assert "8020 endurance" in result
    assert "get_custom_zones" in result


def test_format_sport_settings_custom_zones_without_names():
    """Without the name lookup the ids are still surfaced, not dropped."""
    s = AthleteSportSettings(types=["Run"], custom_zones_ids=[945743])
    result = format_sport_settings(s)
    assert "945743" in result
    assert "get_custom_zones" in result


def test_format_sport_settings_no_custom_zones_line_when_unlinked():
    """Sports with no custom zone set get no pointer line."""
    s = AthleteSportSettings(types=["Swim"], lthr=165)
    assert "get_custom_zones" not in format_sport_settings(s)
```

Append to `tests/test_server.py`:

```python
def test_get_sport_settings_names_linked_zone_set(monkeypatch):
    """get_sport_settings fetches zone set names so it can point at get_custom_zones."""
    _patch_zone_endpoints(monkeypatch)
    result = asyncio.run(get_sport_settings(athlete_id="i1"))
    assert "Run, VirtualRun, TrailRun" in result
    assert "8020 endurance" in result
    assert "get_custom_zones" in result


def test_get_sport_settings_degrades_when_custom_items_fail(monkeypatch):
    """A failed custom-item fetch must not fail the whole call."""
    async def fake_request(url, *_args, **_kwargs):
        if "sport-settings" in url:
            return SPORT_SETTINGS_WITH_ZONES
        return {"error": True, "message": "Rate limited"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_sport_settings(athlete_id="i1"))
    assert "LTHR: 170" in result
    assert "945743" in result
    assert "Rate limited" not in result
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_formatting.py tests/test_server.py -k "sport_settings" -v`

Expected: FAIL — `format_sport_settings() got an unexpected keyword argument 'zone_set_names'`,
and `Sport: Run, TrailRun` not found.

- [ ] **Step 3: Implement the formatter**

Replace `format_sport_settings` in `formatting.py`:

```python
def _label_zones(values: list[Any], names: list[str]) -> str:
    """Pair zone boundary values with their names when the API supplied a matching set."""
    if not values:
        return "N/A"
    if len(names) != len(values):
        return str(values)
    return ", ".join(f"{name} {value}" for name, value in zip(names, values))


def format_sport_settings(
    setting: AthleteSportSettings,
    zone_set_names: dict[int, str] | None = None,
) -> str:
    """Format sport settings into a readable string.

    zone_set_names maps custom item id to zone set name; without it, linked sets are
    identified by id alone.
    """
    lines = [
        f"Sport: {', '.join(setting.types) if setting.types else _fmt(setting.type)}",
        f"FTP: {_fmt(setting.ftp)}",
        f"LTHR: {_fmt(setting.lthr)}",
        f"Max HR: {_fmt(setting.max_hr)}",
        f"Pace zones: {_label_zones(setting.pace_zones, setting.pace_zone_names)}",
        f"Warmup: {_fmt(setting.warmup_time)} s",
        f"Cooldown: {_fmt(setting.cooldown_time)} s",
    ]
    if setting.power_zones:
        lines.append(f"Power zones: {_label_zones(setting.power_zones, setting.power_zone_names)}")
    if setting.hr_zones:
        lines.append(f"HR zones: {_label_zones(setting.hr_zones, setting.hr_zone_names)}")
    if setting.custom_zones_ids:
        names = [
            (zone_set_names or {}).get(item_id) or f"id {item_id}"
            for item_id in setting.custom_zones_ids
        ]
        lines.append(
            f"Custom zone sets: {', '.join(names)} "
            "(call get_custom_zones for CZ codes and resolved bpm/watts)"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Implement the tool change**

Replace the body of `get_sport_settings` in `tools/athlete.py` after the error check. The custom-item
request is made only when at least one group actually links a zone set, so sports without custom
zones cost no extra call:

```python
    result = await make_intervals_request(url=url, api_key=api_key)

    if isinstance(result, dict) and result.get("error"):
        return f"Error fetching sport settings: {result.get('message', 'Unknown error')}"

    if sport_type:
        if not isinstance(result, dict):
            return "Unexpected response from API."
        try:
            setting = AthleteSportSettings.from_dict(result)
        except (TypeError, KeyError, ValueError) as e:
            logger.error("Failed to parse sport settings: %s", e, exc_info=True)
            return "Error: Failed to parse sport settings."
        names = await _fetch_zone_set_names(athlete_id_to_use, api_key, [setting])
        return format_sport_settings(setting, names)

    groups = _parse_sport_groups(result)
    if not groups:
        return "No sport settings found."
    names = await _fetch_zone_set_names(athlete_id_to_use, api_key, groups)
    return "\n\n---\n\n".join(format_sport_settings(g, names) for g in groups)
```

Add the helper next to the other private helpers:

```python
async def _fetch_zone_set_names(
    athlete_id: str,
    api_key: str | None,
    groups: list[AthleteSportSettings],
) -> dict[int, str]:
    """Look up custom zone set names by id, or return empty if none are linked or the fetch fails."""
    if not any(g.custom_zones_ids for g in groups):
        return {}
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/custom-item", api_key=api_key
    )
    if isinstance(result, dict) and result.get("error"):
        logger.warning("Could not fetch custom zone set names: %s", result.get("message"))
        return {}
    return {
        item_id: zone_set.name or f"id {item_id}"
        for item_id, zone_set in _parse_zone_sets(result).items()
    }
```

Note this drops the old per-entry `[Sport setting 'X': failed to format]` placeholder in favour of
`_parse_sport_groups`, which logs and skips unparseable entries. Update
`test_get_sport_settings_list_parse_failure_shows_placeholder` (around `tests/test_server.py:1664`)
to assert the good entry still renders and the bad one is absent, and rename it to
`test_get_sport_settings_list_parse_failure_skips_entry`.

- [ ] **Step 5: Run the full suite**

```bash
uv run pytest -q && uv run ruff check . && uv run mypy src tests
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/intervals_mcp_server/utils/formatting.py src/intervals_mcp_server/tools/athlete.py \
        tests/test_formatting.py tests/test_server.py
git commit -m "feat: label zone boundaries and point at custom zone sets

get_sport_settings now renders the sport group name, pairs zone
boundaries with the names the API already returns, and names any linked
custom zone set so the model knows to call get_custom_zones."
```

---

### Task 7: Document the tool

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md` (the `tools/` module layout line)

**Interfaces:**
- Consumes: the finished `get_custom_zones` tool.
- Produces: no code.

- [ ] **Step 1: Update CLAUDE.md**

In the "Module layout" section, change `athlete.py` from `(3)` to `(4)`:

```
- `src/intervals_mcp_server/tools/` — MCP tools: `activities.py` (6), `events.py` (6), `wellness.py` (1), `athlete.py` (4), `custom_items.py` (5), `search.py` (2), `workouts.py` (3), `seasons.py` (3)
```

Add to the "Key design decisions" list:

```
- **Custom zones vs standard zones**: `get_sport_settings` returns the standard zone model. Custom zones (referenced in workout text as `CZ` + zone id, e.g. `CZZ2`) live in custom items of type `ZONES`, linked via `custom_zones_ids`, and are resolved by `get_custom_zones`. The two must never be mapped onto each other.
```

- [ ] **Step 2: Update README.md**

The README has no per-tool list. Add this subsection at the end of "## Usage with Claude",
immediately before the `## Usage with ChatGPT` heading (around line 169):

```markdown
### Custom zones

Intervals.icu workout text references custom zones as `CZ` + the zone id — for example
`- 10m CZZ2 HR`. Those bands are stored as fractions of the sport's LTHR or FTP, separately from
the standard zone model returned by `get_sport_settings`. Call `get_custom_zones` to list the
codes with their resolved heart rates or watts.
```

- [ ] **Step 3: Verify and commit**

```bash
uv run pytest -q && uv run ruff check . && uv run mypy src tests
git add README.md CLAUDE.md
git commit -m "docs: document get_custom_zones and the CZ code convention"
```

---

## Verification

After Task 7, confirm the tool works against the real API (requires a populated `.env`):

```bash
uv run python -c "
import asyncio
from dotenv import load_dotenv
load_dotenv()
from intervals_mcp_server.server import get_custom_zones
print(asyncio.run(get_custom_zones.fn(sport_type='Run')))
"
```

Expected: the Run table with `CZZ2  Zone 2  81-90%  137-153`, matching the values verified during
design.
