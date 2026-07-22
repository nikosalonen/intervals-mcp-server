"""
Unit tests for the Value dataclass in intervals_mcp_server.utils.types.

These tests verify that the Value dataclass correctly handles:
- String formatting for percent FTP units
- Ramp intervals (start/end values)
- Pace unit deserialization (regression for units missing from ValueUnits)
"""

import pytest

from intervals_mcp_server.utils.types import Value, ValueUnits


def test_str_percent_ftp():
    """Test formatting percentage FTP values."""
    val = Value(value=95.0, units=ValueUnits.PERCENT_FTP)
    assert str(val) == "95% ftp"


def test_str_ramp_percent_ftp():
    """Test formatting ramp intervals with percentage FTP."""
    val = Value(start=65, end=85, units=ValueUnits.PERCENT_FTP)
    assert str(val) == "65%-85% ftp"


@pytest.mark.parametrize(
    "unit_str",
    ["MINS_KM", "MINS_MILE", "SECS_100M", "SECS_100Y", "SECS_500M", "SECS_400M", "SECS_250M"],
)
def test_from_dict_pace_units_round_trip(unit_str):
    """Pace unit strings from the API deserialize and round-trip through to_dict.

    Regression: these units previously raised ValueError in Value.from_dict,
    crashing parsing of running/swimming workout step targets.
    """
    val = Value.from_dict({"value": 5.5, "units": unit_str})
    assert val.units == ValueUnits(unit_str)
    assert val.to_dict()["units"] == unit_str


def test_from_dict_unknown_units_raises():
    """Unknown unit strings still raise ValueError."""
    with pytest.raises(ValueError):
        Value.from_dict({"value": 1.0, "units": "FURLONGS_PER_FORTNIGHT"})
