"""
Sample data for testing Intervals.icu MCP server functions.

This module contains test data structures used across the test suite.
"""

ATHLETE_DATA = {
    "id": "i1",
    "name": "Test Athlete",
    "weight": 70,
    "restingHr": 52,
    "location": "Helsinki",
    "timezone": "Europe/Helsinki",
    "status": "active",
}

SPORT_SETTINGS_DATA = [
    {
        "type": "Ride",
        "ftp": 250,
        "lthr": 165,
        "maxHr": 185,
        "zones": [0, 55, 75, 90, 105, 120],
        "warmup": 600,
        "cooldown": 300,
    },
    {
        "type": "Run",
        "ftp": None,
        "lthr": 165,
        "maxHr": 185,
        "paceZones": [],
        "warmup": 120,
        "cooldown": 120,
    },
]

SINGLE_SPORT_SETTING_DATA = {
    "type": "Ride",
    "ftp": 250,
    "lthr": 165,
    "maxHr": 185,
    "zones": [0, 55, 75, 90, 105, 120],
    "warmup": 600,
    "cooldown": 300,
}

SEARCH_RESULTS_DATA = [
    {
        "id": 101,
        "name": "Morning Ride",
        "startTime": "2024-01-15T08:00:00Z",
        "type": "Ride",
        "distance": 25000,
        "tags": ["commute", "easy"],
    },
    {
        "id": 102,
        "name": "Interval Session",
        "startTime": "2024-01-14T17:00:00Z",
        "type": "Run",
        "distance": 10000,
        "tags": [],
    },
]

WORKOUT_LIBRARY_DATA = [
    {
        "id": "w1",
        "name": "Sweet Spot 2x20",
        "sport": "Ride",
        "type": "Ride",
        "duration": 3600,
        "tss": 65,
        "intervals": [],
    },
]

FOLDER_DATA = [
    {
        "id": "f1",
        "name": "Cycling",
        "workouts": [
            {"id": "w1", "name": "Sweet Spot 2x20"},
            {"id": "w2", "name": "VO2max 30/30"},
        ],
    },
]

BULK_WORKOUT_RESPONSE = [
    {"id": "w10", "name": "New Workout 1"},
    {"id": "w11", "name": "New Workout 2"},
]

TRAINING_PLAN_DATA = {
    "athleteId": "i1",
    "trainingPlanId": 42,
    "trainingPlanStartDate": "2026-03-01",
    "timezone": "Europe/Helsinki",
    "trainingPlanLastApplied": "2026-02-28",
    "trainingPlanAlias": "phase1",
    "trainingPlan": {
        "id": 100,
        "name": "Base Building 8 Weeks",
        "children": [
            {
                "id": 201,
                "name": "Easy Spin",
                "type": "Ride",
                "day": 0,
                "duration": 3600,
            },
            {
                "id": 202,
                "name": "Tempo Run",
                "type": "Run",
                "day": 1,
                "duration": 2400,
            },
            {
                "id": 203,
                "name": "Long Ride",
                "type": "Ride",
                "day": 5,
                "duration": 7200,
            },
        ],
    },
}

SEASON_DATA = [
    {
        "id": 1001,
        "start_date_local": "2026-01-01",
        "end_date_local": "2026-03-31",
        "name": "Base",
        "description": "Aerobic base building phase",
        "category": "SEASON_START",
        "color": "#4CAF50",
        "tags": ["base", "aerobic"],
    },
    {
        "id": 1002,
        "start_date_local": "2026-04-01",
        "end_date_local": "2026-06-30",
        "name": "Build",
        "description": "Intensity build phase",
        "category": "SEASON_START",
        "color": "#FF9800",
        "tags": ["build"],
    },
]

SINGLE_SEASON_DATA = {
    "id": 1001,
    "start_date_local": "2026-01-01",
    "end_date_local": "2026-03-31",
    "name": "Base",
    "description": "Aerobic base building phase",
    "category": "SEASON_START",
    "color": "#4CAF50",
    "tags": ["base", "aerobic"],
}

INTERVALS_DATA = {
    "id": "i1",
    "analyzed": True,
    "icu_intervals": [
        {
            "type": "work",
            "label": "Rep 1",
            "elapsed_time": 60,
            "moving_time": 60,
            "distance": 100,
            "average_watts": 200,
            "max_watts": 300,
            "average_watts_kg": 3.0,
            "max_watts_kg": 5.0,
            "weighted_average_watts": 220,
            "intensity": 0.8,
            "training_load": 10,
            "average_heartrate": 150,
            "max_heartrate": 160,
            "average_cadence": 90,
            "max_cadence": 100,
            "average_speed": 6,
            "max_speed": 8,
        }
    ],
}
