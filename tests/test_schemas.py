"""
Unit tests for the schema classes in intervals_mcp_server.utils.schemas.

Tests verify that from_dict() correctly maps API response fields (including camelCase
aliases) to typed dataclass attributes, and that to_dict() produces valid request bodies.
"""

from intervals_mcp_server.utils.schemas import (
    Activity,
    ActivityInterval,
    ActivityMessage,
    AthleteSportSettings,
    Athlete,
    CustomItem,
    EventRequest,
    EventResponse,
    EventWorkout,
    Folder,
    IntervalsData,
    WellnessEntry,
    Workout,
)


# ── Activity ──────────────────────────────────────────────────────────────


def test_activity_from_dict_snake_case():
    """Activity.from_dict() maps standard snake_case spec fields."""
    data = {
        "id": "abc123",
        "name": "Evening Run",
        "type": "Run",
        "start_date": "2024-03-01T18:00:00Z",
        "distance": 10000.0,
        "elapsed_time": 3600,
        "icu_training_load": 80,
        "icu_average_watts": 250,
        "average_heartrate": 145,
    }
    a = Activity.from_dict(data)
    assert a.id == "abc123"
    assert a.name == "Evening Run"
    assert a.type == "Run"
    assert a.start_date == "2024-03-01T18:00:00Z"
    assert a.distance == 10000.0
    assert a.elapsed_time == 3600
    assert a.icu_training_load == 80
    assert a.icu_average_watts == 250
    assert a.average_heartrate == 145


def test_activity_from_dict_camel_case_aliases():
    """Activity.from_dict() maps legacy camelCase API fields to spec names."""
    data = {
        "name": "Morning Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "duration": 7200,
        "elevationGain": 500.0,
        "avgHr": 150,
        "avgPower": 220,
        "trainingLoad": 90,
    }
    a = Activity.from_dict(data)
    assert a.start_date == "2024-01-01T08:00:00Z"
    assert a.elapsed_time == 7200
    assert a.total_elevation_gain == 500.0
    assert a.average_heartrate == 150
    assert a.icu_average_watts == 220
    assert a.icu_training_load == 90


def test_activity_from_dict_zero_values_preserved():
    """from_dict() preserves 0 values rather than treating them as falsy."""
    data = {"elapsed_time": 0, "distance": 0.0, "icu_average_watts": 0}
    a = Activity.from_dict(data)
    assert a.elapsed_time == 0
    assert a.distance == 0.0
    assert a.icu_average_watts == 0


def test_activity_tags_default_empty():
    """Activity.from_dict() defaults tags to empty list when absent."""
    a = Activity.from_dict({})
    assert a.tags == []


# ── ActivityInterval / ActivityIntervalGroup / IntervalsData ──────────────


def test_activity_interval_from_dict():
    """ActivityInterval.from_dict() maps all spec fields."""
    data = {
        "label": "High Effort",
        "type": "work",
        "elapsed_time": 300,
        "average_watts": 320,
        "average_heartrate": 170,
    }
    interval = ActivityInterval.from_dict(data)
    assert interval.label == "High Effort"
    assert interval.type == "work"
    assert interval.elapsed_time == 300
    assert interval.average_watts == 320
    assert interval.average_heartrate == 170


def test_intervals_data_from_dict():
    """IntervalsData.from_dict() creates nested typed objects."""
    data = {
        "id": "act123",
        "analyzed": True,
        "icu_intervals": [
            {"label": "Rep 1", "type": "work", "elapsed_time": 600, "average_watts": 300}
        ],
        "icu_groups": [{"id": "g1", "count": 3, "elapsed_time": 1800}],
    }
    intervals = IntervalsData.from_dict(data)
    assert intervals.id == "act123"
    assert len(intervals.icu_intervals) == 1
    assert intervals.icu_intervals[0].label == "Rep 1"
    assert len(intervals.icu_groups) == 1
    assert intervals.icu_groups[0].id == "g1"
    assert intervals.icu_groups[0].count == 3


# ── WellnessEntry ─────────────────────────────────────────────────────────


def test_wellness_entry_from_dict():
    """WellnessEntry.from_dict() maps camelCase wellness fields."""
    data = {
        "id": "2024-06-01",
        "ctl": 75.0,
        "atl": 80.0,
        "rampRate": 2.5,
        "ctlLoad": 300,
        "atlLoad": 320,
        "restingHR": 48,
        "sleepSecs": 28800,
        "sportInfo": [{"type": "Ride", "eftp": 280.0}],
        "steps": 8000,
    }
    entry = WellnessEntry.from_dict(data)
    assert entry.id == "2024-06-01"
    assert entry.ctl == 75.0
    assert entry.ramp_rate == 2.5
    assert entry.ctl_load == 300
    assert entry.resting_hr == 48
    assert entry.sleep_secs == 28800
    assert entry.steps == 8000
    assert len(entry.sport_info) == 1
    assert entry.sport_info[0].type == "Ride"
    assert entry.sport_info[0].eftp == 280.0


# ── Athlete ───────────────────────────────────────────────────────────────


def test_athlete_from_dict():
    """Athlete.from_dict() maps athlete profile fields including restingHr alias."""
    data = {
        "id": "i42",
        "name": "Test Athlete",
        "weight": 70.5,
        "restingHr": 52,
        "location": "Helsinki",
        "timezone": "Europe/Helsinki",
        "status": "ACTIVE",
    }
    athlete = Athlete.from_dict(data)
    assert athlete.id == "i42"
    assert athlete.name == "Test Athlete"
    assert athlete.weight == 70.5
    assert athlete.icu_resting_hr == 52
    assert athlete.location == "Helsinki"
    assert athlete.timezone == "Europe/Helsinki"
    assert athlete.status == "ACTIVE"


# ── AthleteSportSettings ──────────────────────────────────────────────────


def test_athlete_sport_settings_from_dict():
    """AthleteSportSettings.from_dict() maps sport settings including maxHr and zones aliases."""
    data = {
        "type": "Ride",
        "ftp": 280,
        "lthr": 168,
        "maxHr": 190,
        "zones": [0, 55, 75, 90, 105, 121],
        "warmup": 600,
        "cooldown": 300,
    }
    s = AthleteSportSettings.from_dict(data)
    assert s.type == "Ride"
    assert s.ftp == 280
    assert s.lthr == 168
    assert s.max_hr == 190
    assert s.power_zones == [0, 55, 75, 90, 105, 121]
    assert s.warmup_time == 600
    assert s.cooldown_time == 300


# ── EventResponse / EventRequest / EventWorkout ───────────────────────────


def test_event_response_from_dict_basic():
    """EventResponse.from_dict() maps event fields including date alias."""
    data = {
        "id": 99,
        "date": "2024-08-01",
        "name": "Long Ride",
        "description": "Easy aerobic",
        "race": False,
    }
    e = EventResponse.from_dict(data)
    assert e.id == 99
    assert e.start_date_local == "2024-08-01"
    assert e.name == "Long Ride"
    assert e.race is False
    assert e.workout is None


def test_event_response_from_dict_with_workout():
    """EventResponse.from_dict() creates nested EventWorkout from workout dict."""
    data = {
        "id": 1,
        "start_date_local": "2024-08-01",
        "name": "Interval Day",
        "workout": {
            "id": 5,
            "type": "Ride",
            "moving_time": 3600,
            "icu_training_load": 80,
            "intervals": [1, 2, 3],
        },
    }
    e = EventResponse.from_dict(data)
    assert e.workout is not None
    assert e.workout.id == 5
    assert e.workout.type == "Ride"
    assert e.workout.moving_time == 3600
    assert e.workout.icu_training_load == 80
    assert len(e.workout.intervals) == 3


def test_event_workout_from_dict_aliases():
    """EventWorkout.from_dict() maps duration/tss aliases."""
    data = {"id": 1, "type": "Run", "duration": 1800, "tss": 60}
    w = EventWorkout.from_dict(data)
    assert w.moving_time == 1800
    assert w.icu_training_load == 60


def test_event_request_to_dict():
    """EventRequest.to_dict() produces correct API request body."""
    req = EventRequest(
        start_date_local="2024-09-15T00:00:00",
        name="Race Day",
        category="RACE_A",
        type="Run",
        moving_time=7200,
        distance=42195,
    )
    d = req.to_dict()
    assert d["start_date_local"] == "2024-09-15T00:00:00"
    assert d["name"] == "Race Day"
    assert d["category"] == "RACE_A"
    assert d["type"] == "Run"
    assert d["moving_time"] == 7200
    assert d["distance"] == 42195


def test_event_request_to_dict_omits_none():
    """EventRequest.to_dict() omits None fields."""
    req = EventRequest(start_date_local="2024-01-01T00:00:00", name="Test")
    d = req.to_dict()
    assert "moving_time" not in d
    assert "distance" not in d
    assert "description" not in d


# ── Workout / Folder ──────────────────────────────────────────────────────


def test_workout_from_dict():
    """Workout.from_dict() maps workout library fields including aliases."""
    data = {
        "id": 10,
        "name": "Sweet Spot 2x20",
        "type": "Ride",
        "folderId": 3,
        "duration": 4800,
        "tss": 70,
        "indoor": True,
        "tags": ["ss", "base"],
    }
    w = Workout.from_dict(data)
    assert w.id == 10
    assert w.name == "Sweet Spot 2x20"
    assert w.folder_id == 3
    assert w.moving_time == 4800
    assert w.icu_training_load == 70
    assert w.indoor is True
    assert w.tags == ["ss", "base"]


def test_workout_to_dict_omits_none():
    """Workout.to_dict() omits None fields from request body."""
    w = Workout(name="Test Workout", type="Run", moving_time=1800)
    d = w.to_dict()
    assert d["name"] == "Test Workout"
    assert d["type"] == "Run"
    assert d["moving_time"] == 1800
    assert "id" not in d
    assert "folder_id" not in d
    assert "description" not in d


def test_folder_from_dict():
    """Folder.from_dict() creates nested Workout objects."""
    data = {
        "id": 7,
        "name": "Base Training",
        "workouts": [
            {"id": 1, "name": "Z2 Ride", "type": "Ride"},
            {"id": 2, "name": "Recovery", "type": "Ride"},
        ],
    }
    folder = Folder.from_dict(data)
    assert folder.id == 7
    assert folder.name == "Base Training"
    assert len(folder.workouts) == 2
    assert folder.workouts[0].name == "Z2 Ride"
    assert folder.workouts[1].name == "Recovery"


# ── CustomItem ────────────────────────────────────────────────────────────


def test_custom_item_from_dict():
    """CustomItem.from_dict() maps all custom item fields."""
    data = {
        "id": 99,
        "name": "My Chart",
        "type": "FITNESS_CHART",
        "description": "CTL/ATL chart",
        "visibility": "PRIVATE",
        "content": {"key": "value"},
    }
    item = CustomItem.from_dict(data)
    assert item.id == 99
    assert item.name == "My Chart"
    assert item.type == "FITNESS_CHART"
    assert item.description == "CTL/ATL chart"
    assert item.visibility == "PRIVATE"
    assert item.content == {"key": "value"}


def test_custom_item_to_dict_omits_none():
    """CustomItem.to_dict() omits None fields."""
    item = CustomItem(name="Chart", type="TRACE_CHART")
    d = item.to_dict()
    assert d == {"name": "Chart", "type": "TRACE_CHART"}


# ── ActivityMessage ───────────────────────────────────────────────────────


def test_activity_message_from_dict():
    """ActivityMessage.from_dict() maps message fields."""
    data = {
        "name": "Coach",
        "created": "2024-07-01T10:00:00Z",
        "type": "NOTE",
        "content": "Great effort!",
    }
    msg = ActivityMessage.from_dict(data)
    assert msg.name == "Coach"
    assert msg.created == "2024-07-01T10:00:00Z"
    assert msg.type == "NOTE"
    assert msg.content == "Great effort!"
