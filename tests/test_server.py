"""
Unit tests for the main MCP server tool functions in intervals_mcp_server.server.

These tests use monkeypatching to mock API responses and verify the formatting and output of each tool function:
- get_activities
- get_activity_details
- get_activity_intervals
- get_activity_streams
- get_activity_messages
- add_activity_message
- get_events
- get_event_by_id
- add_or_update_event
- get_wellness_data

The tests ensure that the server's public API returns expected strings and handles data correctly.
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import (  # pylint: disable=wrong-import-position
    add_activity_message,
    add_or_update_event,
    create_bulk_events,
    create_bulk_workouts,
    get_activities,
    get_activity_details,
    get_activity_intervals,
    get_activity_messages,
    get_activity_streams,
    get_athlete,
    get_event_by_id,
    get_events,
    get_sport_settings,
    get_wellness_data,
    get_custom_items,
    get_custom_item_by_id,
    create_custom_item,
    update_custom_item,
    delete_custom_item,
    list_folders,
    list_workouts,
    search_activities,
    search_intervals,
)
from tests.sample_data import (  # pylint: disable=wrong-import-position
    ATHLETE_DATA,
    BULK_WORKOUT_RESPONSE,
    FOLDER_DATA,
    INTERVALS_DATA,
    SEARCH_RESULTS_DATA,
    SINGLE_SPORT_SETTING_DATA,
    SPORT_SETTINGS_DATA,
    WORKOUT_LIBRARY_DATA,
)


def test_get_activities(monkeypatch):
    """
    Test get_activities returns a formatted string containing activity details when given a sample activity.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return [sample]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activities(athlete_id="1", limit=1, include_unnamed=True))
    assert "Morning Ride" in result
    assert "Activities:" in result


def test_get_activity_details(monkeypatch):
    """
    Test get_activity_details returns a formatted string with the activity name and details.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(123))
    assert "Activity: Morning Ride" in result


def test_get_events(monkeypatch):
    """
    Test get_events returns a formatted string containing event details when given a sample event.
    """
    event = {
        "date": "2024-01-01",
        "id": "e1",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return [event]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_events(athlete_id="1", start_date="2024-01-01", end_date="2024-01-02"))
    assert "Test Event" in result
    assert "Events:" in result


def test_get_event_by_id(monkeypatch):
    """
    Test get_event_by_id returns a formatted string with event details for a given event ID.
    """
    event = {
        "id": "e1",
        "date": "2024-01-01",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return event

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_event_by_id("e1", athlete_id="1"))
    assert "Event Details:" in result
    assert "Test Event" in result


def test_get_wellness_data(monkeypatch):
    """
    Test get_wellness_data returns a formatted string containing wellness data for a given athlete.
    """
    wellness = {
        "2024-01-01": {
            "id": "2024-01-01",
            "ctl": 75,
            "sleepSecs": 28800,
        }
    }

    async def fake_request(*_args, **_kwargs):
        return wellness

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1"))
    assert "Wellness Data:" in result
    assert "2024-01-01" in result


def test_get_activity_intervals(monkeypatch):
    """
    Test get_activity_intervals returns a formatted string with interval analysis for a given activity.
    """

    async def fake_request(*_args, **_kwargs):
        return INTERVALS_DATA

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_intervals("123"))
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result


def test_get_activity_streams(monkeypatch):
    """
    Test get_activity_streams returns a formatted string with stream data for a given activity.
    """
    sample_streams = [
        {
            "type": "time",
            "name": "time",
            "data": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "data2": [],
            "valueType": "time_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "watts",
            "name": "watts",
            "data": [150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200],
            "data2": [],
            "valueType": "power_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "heartrate",
            "name": "heartrate",
            "data": [120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170],
            "data2": [],
            "valueType": "hr_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_streams

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_streams("i107537962"))
    assert "Activity Streams" in result
    assert "time" in result
    assert "watts" in result
    assert "heartrate" in result
    assert "Data Points: 11" in result


def test_add_or_update_event(monkeypatch):
    """
    Test add_or_update_event successfully posts an event and returns the response data.
    """
    expected_response = {
        "id": "e123",
        "start_date_local": "2024-01-15T00:00:00",
        "category": "WORKOUT",
        "name": "Test Workout",
        "type": "Ride",
    }

    async def fake_post_request(*_args, **_kwargs):
        return expected_response

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_post_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_post_request
    )
    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1", start_date="2024-01-15", name="Test Workout", workout_type="Ride"
        )
    )
    assert "Successfully created event:" in result
    assert '"id": "e123"' in result
    assert '"name": "Test Workout"' in result


def test_create_bulk_events(monkeypatch):
    """Test create_bulk_events returns success with count."""
    bulk_response = [
        {"id": 1, "start_date_local": "2024-03-15T00:00:00", "category": "WORKOUT", "name": "Easy Run"},
        {"id": 2, "start_date_local": "2024-03-16T00:00:00", "category": "NOTE", "name": "Rest Day"},
    ]

    async def fake_request(*_args, **_kwargs):
        return bulk_response

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=[
                {"start_date_local": "2024-03-15T00:00:00", "category": "WORKOUT", "name": "Easy Run", "type": "Run"},
                {"start_date_local": "2024-03-16T00:00:00", "category": "NOTE", "name": "Rest Day"},
            ],
        )
    )
    assert "Successfully created/updated 2 event(s)" in result


def test_create_bulk_events_empty(monkeypatch):
    """Test create_bulk_events with empty list returns message."""
    result = asyncio.run(create_bulk_events(athlete_id="i1", events=[]))
    assert "No events provided" in result


def test_create_bulk_events_error(monkeypatch):
    """Test create_bulk_events handles API errors."""
    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Invalid event data"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=[{"start_date_local": "2024-03-15T00:00:00", "category": "WORKOUT", "name": "Bad"}],
        )
    )
    assert "Error creating bulk events" in result
    assert "Invalid event data" in result


def test_create_bulk_events_passes_upsert_params(monkeypatch):
    """Test create_bulk_events passes upsert query parameters correctly."""
    captured_kwargs = {}

    async def fake_request(*_args, **kwargs):
        captured_kwargs.update(kwargs)
        return [{"id": 1, "name": "Updated"}]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=[{"start_date_local": "2024-03-15T00:00:00", "category": "WORKOUT", "name": "Run", "uid": "w1"}],
            upsert_on_uid=True,
            update_plan_applied=True,
        )
    )
    assert "Successfully created/updated 1 event(s)" in result
    assert captured_kwargs["params"]["upsertOnUid"] is True
    assert captured_kwargs["params"]["updatePlanApplied"] is True


def test_create_bulk_events_rejects_non_dict_items(monkeypatch):
    """Test create_bulk_events rejects non-dict items and does not call the API."""
    api_called = False

    async def fake_request(*_args, **_kwargs):
        nonlocal api_called
        api_called = True
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=["not a dict", 42],  # type: ignore[list-item]
        )
    )
    assert "Invalid event data" in result
    assert "Event 0" in result
    assert "expected a dict" in result
    assert not api_called


def test_create_bulk_events_rejects_missing_required_keys(monkeypatch):
    """Test create_bulk_events rejects dicts missing required keys and does not call the API."""
    api_called = False

    async def fake_request(*_args, **_kwargs):
        nonlocal api_called
        api_called = True
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=[{"name": "Missing fields"}],
        )
    )
    assert "Invalid event data" in result
    assert "start_date_local" in result
    assert "category" in result
    assert not api_called


def test_create_bulk_events_rejects_invalid_optional_types(monkeypatch):
    """Test create_bulk_events rejects events with wrong optional field types."""
    api_called = False

    async def fake_request(*_args, **_kwargs):
        nonlocal api_called
        api_called = True
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_events(
            athlete_id="i1",
            events=[{
                "start_date_local": "2024-03-15T00:00:00",
                "category": "WORKOUT",
                "name": "Run",
                "indoor": "yes",  # should be bool
                "tags": "not-a-list",  # should be list of strings
            }],
        )
    )
    assert "Invalid event data" in result
    assert "'indoor' must be" in result
    assert "'tags' must be a list of strings" in result
    assert not api_called


def test_get_activity_messages(monkeypatch):
    """Test get_activity_messages returns formatted messages for an activity."""
    sample_messages = [
        {
            "id": 1,
            "name": "Niko",
            "created": "2024-06-15T10:30:00Z",
            "type": "NOTE",
            "content": "Legs felt heavy today",
        },
        {
            "id": 2,
            "name": "Coach",
            "created": "2024-06-15T11:00:00Z",
            "type": "TEXT",
            "content": "Good effort despite that!",
        },
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_messages

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i123"))
    assert "Legs felt heavy today" in result
    assert "Good effort despite that!" in result
    assert "Niko" in result
    assert "Coach" in result


def test_get_activity_messages_error(monkeypatch):
    """Test get_activity_messages handles API errors gracefully."""

    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Activity not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i999"))
    assert "Error fetching activity messages" in result
    assert "Activity not found" in result


def test_get_activity_messages_empty(monkeypatch):
    """Test get_activity_messages returns appropriate message when no messages exist."""

    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i123"))
    assert "No messages found" in result


def test_add_activity_message(monkeypatch):
    """Test add_activity_message posts a message and returns confirmation."""

    async def fake_request(*_args, **kwargs):
        assert kwargs.get("method") == "POST"
        assert kwargs.get("data") == {"content": "Great run!"}
        return {"id": 42, "new_chat": None}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Great run!"))
    assert "Successfully added message" in result
    assert "42" in result


def test_add_activity_message_missing_id(monkeypatch):
    """Test add_activity_message warns when response has no ID."""

    async def fake_request(*_args, **_kwargs):
        return {"new_chat": None}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Hello"))
    assert "appears to have been added" in result
    assert "verify manually" in result


def test_add_activity_message_unexpected_response(monkeypatch):
    """Test add_activity_message handles unexpected non-dict response."""

    async def fake_request(*_args, **_kwargs):
        return None

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Hello"))
    assert "Unexpected response" in result


def test_add_activity_message_error(monkeypatch):
    """Test add_activity_message handles API errors."""

    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i999", content="Hello"))
    assert "Error adding message" in result


def test_get_custom_items(monkeypatch):
    """
    Test get_custom_items returns a formatted string containing custom item details.
    """
    custom_items = [
        {"id": 1, "name": "HR Zones", "type": "ZONES", "description": "Heart rate zones"},
        {"id": 2, "name": "Power Chart", "type": "FITNESS_CHART", "description": None},
    ]

    async def fake_request(*_args, **_kwargs):
        return custom_items

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_items(athlete_id="1"))
    assert "Custom Items:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Power Chart" in result


def test_get_custom_item_by_id(monkeypatch):
    """
    Test get_custom_item_by_id returns formatted details of a single custom item.
    """
    custom_item = {
        "id": 1,
        "name": "HR Zones",
        "type": "ZONES",
        "description": "Heart rate zones",
        "visibility": "PRIVATE",
        "index": 0,
    }

    async def fake_request(*_args, **_kwargs):
        return custom_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_item_by_id(item_id=1, athlete_id="1"))
    assert "Custom Item Details:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Heart rate zones" in result
    assert "PRIVATE" in result


def test_create_custom_item(monkeypatch):
    """
    Test create_custom_item returns a success message with formatted item details.
    """
    created_item = {
        "id": 10,
        "name": "New Chart",
        "type": "FITNESS_CHART",
        "description": "A new fitness chart",
        "visibility": "PRIVATE",
    }

    async def fake_request(*_args, **_kwargs):
        return created_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(name="New Chart", item_type="FITNESS_CHART", athlete_id="1")
    )
    assert "Successfully created custom item:" in result
    assert "New Chart" in result
    assert "FITNESS_CHART" in result


def test_create_custom_item_with_string_content(monkeypatch):
    """
    Test create_custom_item correctly parses content when passed as a JSON string.
    """
    captured: dict = {}

    async def fake_request(*_args, **kwargs):
        captured["data"] = kwargs.get("data")
        return {
            "id": 11,
            "name": "Activity Field",
            "type": "ACTIVITY_FIELD",
            "content": {"expression": "icu_training_load"},
        }

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Activity Field",
            item_type="ACTIVITY_FIELD",
            athlete_id="1",
            content='{"expression": "icu_training_load"}',  # type: ignore[arg-type]
        )
    )
    assert "Successfully created custom item:" in result
    # Verify the content was parsed from string to dict before being sent
    assert isinstance(captured["data"]["content"], dict)
    assert captured["data"]["content"]["expression"] == "icu_training_load"


def test_update_custom_item(monkeypatch):
    """
    Test update_custom_item returns a success message with formatted item details.
    """
    updated_item = {
        "id": 1,
        "name": "Updated Chart",
        "type": "FITNESS_CHART",
        "description": "Updated description",
        "visibility": "PUBLIC",
    }

    async def fake_request(*_args, **_kwargs):
        return updated_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        update_custom_item(item_id=1, name="Updated Chart", athlete_id="1")
    )
    assert "Successfully updated custom item:" in result
    assert "Updated Chart" in result
    assert "PUBLIC" in result


def test_delete_custom_item(monkeypatch):
    """
    Test delete_custom_item returns the API response.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(delete_custom_item(item_id=1, athlete_id="1"))
    assert "Successfully deleted" in result


def test_create_custom_item_with_invalid_json_content(monkeypatch):
    """
    Test create_custom_item returns an error message when content is an invalid JSON string.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Bad Item",
            item_type="FITNESS_CHART",
            athlete_id="1",
            content="not valid json",  # type: ignore[arg-type]
        )
    )
    assert "Error: content must be valid JSON when passed as a string." in result


def test_get_athlete(monkeypatch):
    """Test get_athlete returns formatted athlete profile."""
    async def fake_request(*_args, **_kwargs):
        return ATHLETE_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_athlete(athlete_id="1"))
    assert "Test Athlete" in result
    assert "70" in result
    assert "52" in result
    assert "Helsinki" in result


def test_get_athlete_error(monkeypatch):
    """Test get_athlete handles API errors."""
    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_athlete(athlete_id="1"))
    assert "Error fetching athlete" in result
    assert "Not found" in result


def test_get_sport_settings(monkeypatch):
    """Test get_sport_settings returns formatted settings for all sports."""
    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_sport_settings(athlete_id="1"))
    assert "Ride" in result
    assert "250" in result
    assert "Run" in result


def test_get_sport_settings_single(monkeypatch):
    """Test get_sport_settings with sport_type returns single sport."""
    async def fake_request(*_args, **_kwargs):
        return SINGLE_SPORT_SETTING_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.athlete.make_intervals_request", fake_request)
    result = asyncio.run(get_sport_settings(athlete_id="1", sport_type="Ride"))
    assert "Ride" in result
    assert "250" in result
    assert "165" in result


def test_search_activities(monkeypatch):
    """Test search_activities returns formatted search results."""
    async def fake_request(*_args, **_kwargs):
        return SEARCH_RESULTS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    result = asyncio.run(search_activities(athlete_id="1", q="ride"))
    assert "Morning Ride" in result
    assert "Interval Session" in result
    assert "Search results:" in result


def test_search_activities_empty(monkeypatch):
    """Test search_activities when no results."""
    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    result = asyncio.run(search_activities(athlete_id="1", q="nonexistent"))
    assert "No activities found" in result


def test_search_activities_error(monkeypatch):
    """Test search_activities handles API errors."""
    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Server error"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    result = asyncio.run(search_activities(athlete_id="1", q="ride"))
    assert "Error searching activities" in result
    assert "Server error" in result


def test_search_intervals(monkeypatch):
    """Test search_intervals returns formatted results."""
    async def fake_request(*_args, **_kwargs):
        return SEARCH_RESULTS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    result = asyncio.run(
        search_intervals(athlete_id="1", duration_seconds=60, intensity_min=0.9, intensity_max=1.0)
    )
    assert "Morning Ride" in result or "Interval" in result
    assert "Interval search results:" in result or "results" in result


def test_search_intervals_empty(monkeypatch):
    """Test search_intervals when no matching activities."""
    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    result = asyncio.run(
        search_intervals(athlete_id="1", duration_seconds=60, intensity_min=0.95)
    )
    assert "No activities found" in result


def test_list_workouts(monkeypatch):
    """Test list_workouts returns formatted workout library."""
    async def fake_request(*_args, **_kwargs):
        return WORKOUT_LIBRARY_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.make_intervals_request", fake_request)
    result = asyncio.run(list_workouts(athlete_id="1"))
    assert "Sweet Spot 2x20" in result
    assert "Workout library:" in result


def test_list_workouts_empty(monkeypatch):
    """Test list_workouts when library is empty."""
    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.make_intervals_request", fake_request)
    result = asyncio.run(list_workouts(athlete_id="1"))
    assert "No workouts in library" in result


def test_list_folders(monkeypatch):
    """Test list_folders returns formatted folders with workouts."""
    async def fake_request(*_args, **_kwargs):
        return FOLDER_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.make_intervals_request", fake_request)
    result = asyncio.run(list_folders(athlete_id="1"))
    assert "Cycling" in result
    assert "Sweet Spot 2x20" in result
    assert "VO2max 30/30" in result
    assert "Folders:" in result


def test_list_folders_empty(monkeypatch):
    """Test list_folders when no folders."""
    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.make_intervals_request", fake_request)
    result = asyncio.run(list_folders(athlete_id="1"))
    assert "No folders found" in result


def test_create_bulk_workouts(monkeypatch):
    """Test create_bulk_workouts returns success with count."""
    async def fake_request(*_args, **_kwargs):
        return BULK_WORKOUT_RESPONSE

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.workouts.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_workouts(athlete_id="1", workouts=[{"name": "W1", "sport": "Ride"}, {"name": "W2", "sport": "Ride"}])
    )
    assert "Successfully created" in result
    assert "2" in result


def test_create_bulk_workouts_empty(monkeypatch):
    """Test create_bulk_workouts with empty list returns message."""
    result = asyncio.run(create_bulk_workouts(athlete_id="1", workouts=[]))
    assert "No workouts provided" in result


def test_create_bulk_workouts_error(monkeypatch):
    """Test create_bulk_workouts handles API errors."""
    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Invalid workout data"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.workouts.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_bulk_workouts(athlete_id="1", workouts=[{"name": "Bad", "sport": "Ride"}])
    )
    assert "Error creating bulk workouts" in result
    assert "Invalid workout data" in result


# -- Error handling: visible placeholders for parse failures --


def test_get_activities_parse_failure_shows_placeholder(monkeypatch):
    """When an activity fails to parse, the output should contain a visible placeholder."""
    good = {"name": "Good Ride", "id": "a1", "type": "Ride"}
    bad = {"id": "a2", "name": "Bad"}

    original_from_dict = __import__(
        "intervals_mcp_server.utils.schemas", fromlist=["Activity"]
    ).Activity.from_dict

    @classmethod  # type: ignore[misc]
    def flaky_from_dict(cls, data):
        if data.get("id") == "a2":
            raise ValueError("forced parse error")
        return original_from_dict.__func__(cls, data)

    async def fake_request(*_args, **_kwargs):
        return [good, bad]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.activities.Activity.from_dict", flaky_from_dict)

    result = asyncio.run(get_activities(athlete_id="1", limit=10, include_unnamed=True))
    assert "Good Ride" in result
    assert "[Activity a2: failed to format]" in result


def test_get_events_parse_failure_shows_placeholder(monkeypatch):
    """When an event fails to parse, the output should contain a visible placeholder."""
    good = {"id": 1, "name": "Good Event", "start_date_local": "2024-01-01"}
    bad = {"id": 2, "name": "Bad Event"}

    original_from_dict = __import__(
        "intervals_mcp_server.utils.schemas", fromlist=["EventResponse"]
    ).EventResponse.from_dict

    @classmethod  # type: ignore[misc]
    def flaky_from_dict(cls, data):
        if data.get("id") == 2:
            raise TypeError("forced parse error")
        return original_from_dict.__func__(cls, data)

    async def fake_request(*_args, **_kwargs):
        return [good, bad]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.EventResponse.from_dict", flaky_from_dict)

    result = asyncio.run(get_events(athlete_id="1"))
    assert "Good Event" in result
    assert "[Event 2: failed to format]" in result


def test_get_wellness_parse_failure_shows_placeholder(monkeypatch):
    """When a wellness entry fails to parse, the output should contain a visible placeholder."""
    good = {"id": "2024-01-01", "weight": 70}
    bad = {"id": "2024-01-02", "weight": 80}

    original_from_dict = __import__(
        "intervals_mcp_server.utils.schemas", fromlist=["WellnessEntry"]
    ).WellnessEntry.from_dict

    @classmethod  # type: ignore[misc]
    def flaky_from_dict(cls, data):
        if data.get("id") == "2024-01-02":
            raise KeyError("forced parse error")
        return original_from_dict.__func__(cls, data)

    async def fake_request(*_args, **_kwargs):
        return [good, bad]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.WellnessEntry.from_dict", flaky_from_dict)

    result = asyncio.run(get_wellness_data(athlete_id="1"))
    assert "Weight: 70" in result
    assert "[Wellness data for 2024-01-02: failed to format]" in result


def test_get_activity_details_parse_failure_returns_error(monkeypatch):
    """When a single activity fails to parse, a clear error message is returned."""
    async def fake_request(*_args, **_kwargs):
        return {"id": "a1", "name": "Bad Activity"}

    @classmethod  # type: ignore[misc]
    def bad_from_dict(cls, data):
        raise ValueError("forced parse error")

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.activities.Activity.from_dict", bad_from_dict)

    result = asyncio.run(get_activity_details(activity_id="a1"))
    assert "Error" in result
    assert "a1" in result


def test_list_workouts_parse_failure_shows_placeholder(monkeypatch):
    """When a workout fails to parse, the output should contain a visible placeholder."""
    good = {"id": 1, "name": "Good Workout", "type": "Ride"}
    bad = {"id": 2, "name": "Bad Workout"}

    original_from_dict = __import__(
        "intervals_mcp_server.utils.schemas", fromlist=["Workout"]
    ).Workout.from_dict

    @classmethod  # type: ignore[misc]
    def flaky_from_dict(cls, data):
        if data.get("id") == 2:
            raise ValueError("forced parse error")
        return original_from_dict.__func__(cls, data)

    async def fake_request(*_args, **_kwargs):
        return [good, bad]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.workouts.Workout.from_dict", flaky_from_dict)

    result = asyncio.run(list_workouts(athlete_id="1"))
    assert "Good Workout" in result
    assert "[Workout 2: failed to format]" in result


def test_search_activities_parse_failure_shows_placeholder(monkeypatch):
    """When a search result fails to parse, the output should contain a visible placeholder."""
    good = {"id": "a1", "name": "Good"}
    bad = {"id": "a2", "name": "Bad"}

    original_from_dict = __import__(
        "intervals_mcp_server.utils.schemas", fromlist=["Activity"]
    ).Activity.from_dict

    @classmethod  # type: ignore[misc]
    def flaky_from_dict(cls, data):
        if data.get("id") == "a2":
            raise TypeError("forced parse error")
        return original_from_dict.__func__(cls, data)

    async def fake_request(*_args, **_kwargs):
        return [good, bad]

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.search.Activity.from_dict", flaky_from_dict)

    result = asyncio.run(search_activities(athlete_id="1"))
    assert "Good" in result
    assert "[Search result a2: failed to format]" in result
