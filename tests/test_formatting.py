"""
Unit tests for formatting utilities in intervals_mcp_server.utils.formatting.

These tests verify that the formatting functions produce expected output strings for activities, workouts, wellness entries, events, and intervals.
"""

import json
from intervals_mcp_server.utils.formatting import (
    _fmt,
    _fmt_datetime,
    format_activity_message,
    format_activity_summary,
    format_athlete_summary,
    format_custom_item_details,
    format_event_details,
    format_event_summary,
    format_folder_summary,
    format_intervals,
    format_search_result,
    format_sport_settings,
    format_wellness_entry,
    format_workout,
)
from intervals_mcp_server.utils.schemas import (
    Activity,
    ActivityMessage,
    Athlete,
    AthleteSportSettings,
    CustomItem,
    EventResponse,
    Folder,
    IntervalsData,
    WellnessEntry,
    Workout,
)
from tests.sample_data import INTERVALS_DATA


def test_format_activity_summary():
    """
    Test that format_activity_summary returns a string containing the activity name and ID.
    """
    data = {
        "name": "Morning Ride",
        "id": 1,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }
    result = format_activity_summary(Activity.from_dict(data))
    assert "Activity: Morning Ride" in result
    assert "ID: 1" in result


def test_format_workout():
    """
    Test that format_workout returns a string containing the workout name.
    """
    workout = {
        "name": "Workout1",
        "description": "desc",
        "type": "Ride",
        "moving_time": 3600,
        "icu_training_load": 50,
    }
    result = format_workout(Workout.from_dict(workout))
    assert "Workout: Workout1" in result


def test_format_wellness_entry():
    """
    Test that format_wellness_entry returns a string containing the date and fitness (CTL).
    """
    with open("tests/ressources/wellness_entry.json", "r", encoding="utf-8") as f:
        entry = json.load(f)
    result = format_wellness_entry(WellnessEntry.from_dict(entry))

    with open("tests/ressources/wellness_entry_formatted.txt", "r", encoding="utf-8") as f:
        expected_result = f.read()
    assert result == expected_result


def test_format_event_summary():
    """
    Test that format_event_summary returns a string containing the event date and type.
    """
    event = {
        "start_date_local": "2024-01-01",
        "id": "e1",
        "name": "Event1",
        "description": "desc",
        "race": True,
    }
    summary = format_event_summary(EventResponse.from_dict(event))
    assert "Date: 2024-01-01" in summary
    assert "Type: Race" in summary


def test_format_event_details():
    """
    Test that format_event_details returns a string containing event and workout details.
    """
    event = {
        "id": "e1",
        "date": "2024-01-01",
        "name": "Event1",
        "description": "desc",
        "workout": {
            "id": "w1",
            "type": "Ride",
            "moving_time": 3600,
            "icu_training_load": 50,
            "intervals": [1, 2],
        },
        "race": True,
        "priority": "A",
        "result": "1st",
        "calendar": {"name": "Main"},
    }
    details = format_event_details(EventResponse.from_dict(event))
    assert "Event Details:" in details
    assert "Workout Information:" in details


def test_format_intervals():
    """
    Test that format_intervals returns a string containing interval analysis and the interval label.
    """
    result = format_intervals(IntervalsData.from_dict(INTERVALS_DATA))
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result


# ── _fmt() helper tests ──────────────────────────────────────────────────


def test_fmt_none_returns_default():
    """_fmt() returns default when value is None."""
    assert _fmt(None) == "N/A"
    assert _fmt(None, "Unknown") == "Unknown"


def test_fmt_preserves_falsy_values():
    """_fmt() preserves falsy non-None values (0, empty string, False)."""
    assert _fmt(0) == 0
    assert _fmt("") == ""
    assert _fmt(False) is False
    assert _fmt([]) == []


def test_fmt_passes_through_truthy():
    """_fmt() passes through non-None values unchanged."""
    assert _fmt(42) == 42
    assert _fmt("hello") == "hello"


# ── _fmt_datetime() helper tests ─────────────────────────────────────────


def test_fmt_datetime_none():
    """_fmt_datetime() returns 'Unknown' for None."""
    assert _fmt_datetime(None) == "Unknown"


def test_fmt_datetime_empty_string():
    """_fmt_datetime() returns 'Unknown' for empty string."""
    assert _fmt_datetime("") == "Unknown"


def test_fmt_datetime_short_date():
    """_fmt_datetime() returns short dates (<=10 chars) unchanged."""
    assert _fmt_datetime("2024-01-01") == "2024-01-01"


def test_fmt_datetime_iso_with_z():
    """_fmt_datetime() parses ISO datetime with Z suffix."""
    assert _fmt_datetime("2024-01-01T08:00:00Z") == "2024-01-01 08:00:00"


def test_fmt_datetime_iso_with_offset():
    """_fmt_datetime() parses ISO datetime with timezone offset."""
    result = _fmt_datetime("2024-01-01T08:00:00+02:00")
    assert result == "2024-01-01 08:00:00"


def test_fmt_datetime_malformed():
    """_fmt_datetime() returns raw value for unparseable strings."""
    assert _fmt_datetime("not-a-date-at-all") == "not-a-date-at-all"


# ── format_athlete_summary tests ─────────────────────────────────────────


def test_format_athlete_summary():
    """format_athlete_summary() includes athlete profile fields."""
    athlete = Athlete(
        id="i42",
        name="Test Athlete",
        weight=70.5,
        icu_resting_hr=52,
        location="Helsinki",
        timezone="Europe/Helsinki",
        status="ACTIVE",
    )
    result = format_athlete_summary(athlete)
    assert "Athlete: Test Athlete" in result
    assert "ID: i42" in result
    assert "Weight: 70.5 kg" in result
    assert "Resting HR: 52 bpm" in result
    assert "Location: Helsinki" in result
    assert "Status: ACTIVE" in result


# ── format_sport_settings tests ──────────────────────────────────────────


def test_format_sport_settings():
    """format_sport_settings() includes FTP, zones, warmup/cooldown."""
    s = AthleteSportSettings(
        type="Ride",
        ftp=280,
        lthr=168,
        max_hr=190,
        power_zones=[0, 55, 75, 90, 105, 121],
        warmup_time=600,
        cooldown_time=300,
    )
    result = format_sport_settings(s)
    assert "Sport: Ride" in result
    assert "FTP: 280" in result
    assert "LTHR: 168" in result
    assert "Max HR: 190" in result
    assert "Power zones:" in result
    assert "Warmup: 600 s" in result
    assert "Cooldown: 300 s" in result


# ── format_search_result tests ───────────────────────────────────────────


def test_format_search_result():
    """format_search_result() formats lightweight activity search result."""
    a = Activity(
        id="101",
        name="Morning Ride",
        start_date="2024-01-15T08:00:00Z",
        type="Ride",
        distance=25000.0,
        tags=["commute", "easy"],
    )
    result = format_search_result(a)
    assert "ID: 101" in result
    assert "Morning Ride" in result
    assert "2024-01-15 08:00:00" in result
    assert "25000" in result
    assert "commute, easy" in result


# ── format_folder_summary tests ──────────────────────────────────────────


def test_format_folder_summary():
    """format_folder_summary() includes folder name, ID, and workout names."""
    folder = Folder(
        id=7,
        name="Base Training",
        workouts=[
            Workout(name="Z2 Ride"),
            Workout(name="Recovery"),
        ],
    )
    result = format_folder_summary(folder)
    assert "Folder: Base Training" in result
    assert "ID: 7" in result
    assert "Workouts: 2" in result
    assert "- Z2 Ride" in result
    assert "- Recovery" in result


# ── format_custom_item_details tests ─────────────────────────────────────


def test_format_custom_item_details():
    """format_custom_item_details() includes all custom item fields."""
    item = CustomItem(
        id=99,
        name="My Chart",
        type="FITNESS_CHART",
        description="CTL/ATL chart",
        visibility="PRIVATE",
        content={"key": "value"},
    )
    result = format_custom_item_details(item)
    assert "ID: 99" in result
    assert "Name: My Chart" in result
    assert "Type: FITNESS_CHART" in result
    assert "Description: CTL/ATL chart" in result
    assert "Visibility: PRIVATE" in result
    assert '"key": "value"' in result


# ── format_activity_message tests ────────────────────────────────────────


def test_format_activity_message():
    """format_activity_message() formats message with datetime parsing."""
    msg = ActivityMessage(
        name="Coach",
        created="2024-07-01T10:00:00Z",
        type="NOTE",
        content="Great effort!",
    )
    result = format_activity_message(msg)
    assert "Author: Coach" in result
    assert "2024-07-01 10:00:00" in result
    assert "Type: NOTE" in result
    assert "Great effort!" in result


# ── Rich wellness entry test ─────────────────────────────────────────────


def test_format_wellness_entry_rich():
    """format_wellness_entry() with all sections populated."""
    entry = WellnessEntry(
        id="2024-06-01",
        ctl=80.0,
        atl=90.0,
        weight=75.0,
        resting_hr=48,
        sleep_secs=28800,
        sleep_quality=2,
        sleep_score=85.0,
        readiness=8.5,
        menstrual_phase="FOLLICULAR",
        soreness=3,
        fatigue=5,
        stress=4,
        mood=7,
        motivation=8,
        kcal_consumed=2500,
        hydration=7,
        systolic=120,
        diastolic=80,
        steps=10000,
        comments="Good day",
        locked=True,
    )
    result = format_wellness_entry(entry)
    assert "Date: 2024-06-01" in result
    assert "Fitness (CTL): 80.0" in result
    assert "Fatigue (ATL): 90.0" in result
    assert "Weight: 75.0 kg" in result
    assert "Resting HR: 48 bpm" in result
    assert "Sleep: 8.00 hours" in result
    assert "Sleep Quality: 2 (Good)" in result
    assert "Device Sleep Score: 85.0/100" in result
    assert "Readiness: 8.5/10" in result
    assert "Menstrual Phase: Follicular" in result
    assert "Soreness: 3/10" in result
    assert "Fatigue: 5/10" in result
    assert "Blood Pressure: 120/80 mmHg" in result
    assert "Calories Consumed: 2500" in result
    assert "Hydration Score: 7/10" in result
    assert "Steps: 10000" in result
    assert "Comments: Good day" in result
    assert "Status: Locked" in result
