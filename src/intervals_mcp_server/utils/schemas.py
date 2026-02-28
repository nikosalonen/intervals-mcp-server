"""
API response and request schemas for the Intervals.icu MCP Server.

Typed dataclasses and enums derived from the Intervals.icu OpenAPI spec.
Only fields accessed by the MCP tools and formatters are included.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from intervals_mcp_server.utils.types import WorkoutDoc

logger = logging.getLogger(__name__)


def _first(*values: Any) -> Any:
    """Return the first non-None value from the arguments."""
    return next((v for v in values if v is not None), None)


def _get_list(data: dict[str, Any], *keys: str) -> list[Any]:
    """Get the first list value found for the given keys, ignoring non-list values."""
    for key in keys:
        val = data.get(key)
        if isinstance(val, list):
            return val
    return []


def _normalize_tags(raw: Any) -> list[str]:
    """Normalize a raw tags value into a list of strings."""
    if isinstance(raw, list):
        return [str(t) for t in raw if t is not None]
    if raw is None:
        return []
    return [str(raw)]


def _safe_enum(enum_cls: type[StrEnum], value: Any) -> str | None:
    """Try to parse a value as a StrEnum member, falling back to the raw string."""
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return str(value)


def _dict_items(items: list[Any], context: str = "") -> list[dict[str, Any]]:
    """Filter a list to only dict items, logging any skipped non-dict entries."""
    result: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        elif item is not None:
            logger.warning("Skipped non-dict item (type=%s) in %s", type(item).__name__, context)
    return result


# ── Enums ──────────────────────────────────────────────────────────────────


class EventCategory(StrEnum):
    """Event category types for Intervals.icu calendar events."""

    WORKOUT = "WORKOUT"
    RACE_A = "RACE_A"
    RACE_B = "RACE_B"
    RACE_C = "RACE_C"
    NOTE = "NOTE"
    PLAN = "PLAN"
    HOLIDAY = "HOLIDAY"
    SICK = "SICK"
    INJURED = "INJURED"
    SET_EFTP = "SET_EFTP"
    FITNESS_DAYS = "FITNESS_DAYS"
    SEASON_START = "SEASON_START"
    TARGET = "TARGET"
    SET_FITNESS = "SET_FITNESS"


class ActivitySubType(StrEnum):
    """Activity sub-type values."""

    NONE = "NONE"
    COMMUTE = "COMMUTE"
    WARMUP = "WARMUP"
    COOLDOWN = "COOLDOWN"
    RACE = "RACE"


class MenstrualPhase(StrEnum):
    """Menstrual cycle phase values for wellness tracking."""

    PERIOD = "PERIOD"
    FOLLICULAR = "FOLLICULAR"
    OVULATING = "OVULATING"
    LUTEAL = "LUTEAL"
    NONE = "NONE"


class CustomItemType(StrEnum):
    """Custom item type values."""

    FITNESS_CHART = "FITNESS_CHART"
    TRACE_CHART = "TRACE_CHART"
    INPUT_FIELD = "INPUT_FIELD"
    ACTIVITY_FIELD = "ACTIVITY_FIELD"
    INTERVAL_FIELD = "INTERVAL_FIELD"
    ACTIVITY_STREAM = "ACTIVITY_STREAM"
    ACTIVITY_CHART = "ACTIVITY_CHART"
    ACTIVITY_HISTOGRAM = "ACTIVITY_HISTOGRAM"
    ACTIVITY_HEATMAP = "ACTIVITY_HEATMAP"
    ACTIVITY_MAP = "ACTIVITY_MAP"
    ACTIVITY_PANEL = "ACTIVITY_PANEL"
    ZONES = "ZONES"


class CustomItemVisibility(StrEnum):
    """Visibility settings for custom items."""

    PRIVATE = "PRIVATE"
    FOLLOWERS = "FOLLOWERS"
    PUBLIC = "PUBLIC"


class AthleteStatus(StrEnum):
    """Athlete account status values."""

    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    ARCHIVED = "ARCHIVED"


class SportType(StrEnum):
    """Sport type values shared across activities, workouts, and sport settings."""

    RIDE = "Ride"
    RUN = "Run"
    SWIM = "Swim"
    WEIGHT_TRAINING = "WeightTraining"
    HIKE = "Hike"
    WALK = "Walk"
    ALPINE_SKI = "AlpineSki"
    BACKCOUNTRY_SKI = "BackcountrySki"
    BADMINTON = "Badminton"
    CANOEING = "Canoeing"
    CROSSFIT = "Crossfit"
    EBIKE_RIDE = "EBikeRide"
    EMTB_RIDE = "EMountainBikeRide"
    ELLIPTICAL = "Elliptical"
    GOLF = "Golf"
    GRAVEL_RIDE = "GravelRide"
    TRACK_RIDE = "TrackRide"
    HANDCYCLE = "Handcycle"
    HIIT = "HighIntensityIntervalTraining"
    HOCKEY = "Hockey"
    ICE_SKATE = "IceSkate"
    INLINE_SKATE = "InlineSkate"
    KAYAKING = "Kayaking"
    KITESURF = "Kitesurf"
    MTB_RIDE = "MountainBikeRide"
    NORDIC_SKI = "NordicSki"
    OPEN_WATER_SWIM = "OpenWaterSwim"
    PADEL = "Padel"
    PILATES = "Pilates"
    PICKLEBALL = "Pickleball"
    RACQUETBALL = "Racquetball"
    RUGBY = "Rugby"
    ROCK_CLIMBING = "RockClimbing"
    ROLLER_SKI = "RollerSki"
    ROWING = "Rowing"
    SAIL = "Sail"
    SKATEBOARD = "Skateboard"
    SNOWBOARD = "Snowboard"
    SNOWSHOE = "Snowshoe"
    SOCCER = "Soccer"
    SQUASH = "Squash"
    STAIR_STEPPER = "StairStepper"
    SUP = "StandUpPaddling"
    SURFING = "Surfing"
    TABLE_TENNIS = "TableTennis"
    TENNIS = "Tennis"
    TRAIL_RUN = "TrailRun"
    TRANSITION = "Transition"
    VELOMOBILE = "Velomobile"
    VIRTUAL_RIDE = "VirtualRide"
    VIRTUAL_ROW = "VirtualRow"
    VIRTUAL_RUN = "VirtualRun"
    VIRTUAL_SKI = "VirtualSki"
    WATER_SPORT = "WaterSport"
    WHEELCHAIR = "Wheelchair"
    WINDSURF = "Windsurf"
    WORKOUT = "Workout"
    YOGA = "Yoga"
    OTHER = "Other"


# ── Dataclasses ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Activity:
    """Athlete activity response from the Intervals.icu API.

    Fields are a subset of the full Activity schema — only those accessed
    by the MCP tools and formatters are included.
    """

    id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    start_date: str | None = None
    distance: float | None = None
    elapsed_time: int | None = None
    moving_time: int | None = None
    total_elevation_gain: float | None = None
    total_elevation_loss: float | None = None
    trainer: bool | None = None
    average_heartrate: int | None = None
    max_heartrate: int | None = None
    average_cadence: float | None = None
    calories: int | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_temp: float | None = None
    min_temp: int | None = None
    max_temp: int | None = None
    avg_lr_balance: float | None = None
    perceived_exertion: float | None = None
    feel: int | None = None
    session_rpe: int | None = None
    icu_ftp: int | None = None
    icu_training_load: int | None = None
    icu_atl: float | None = None
    icu_ctl: float | None = None
    icu_average_watts: int | None = None
    icu_weighted_avg_watts: int | None = None
    icu_joules: int | None = None
    icu_intensity: float | None = None
    icu_rpe: int | None = None
    icu_power_hr: float | None = None
    icu_variability_index: float | None = None
    icu_resting_hr: int | None = None
    icu_weight: float | None = None
    icu_efficiency_factor: float | None = None
    lthr: int | None = None
    decoupling: float | None = None
    average_stride: float | None = None
    average_wind_speed: float | None = None
    headwind_percent: float | None = None
    tailwind_percent: float | None = None
    trimp: float | None = None
    polarization_index: float | None = None
    power_load: int | None = None
    hr_load: int | None = None
    pace_load: int | None = None
    device_name: str | None = None
    power_meter: str | None = None
    file_type: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Activity":
        """Create an Activity from a raw API response dict.

        Maps select camelCase API aliases (e.g., startTime, avgHr, avgPower) to snake_case fields.
        """
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            type=_safe_enum(SportType, data.get("type")),
            start_date=_first(
                data.get("start_date"),
                data.get("startTime"),
                data.get("start_date_local"),
            ),
            distance=data.get("distance"),
            elapsed_time=_first(data.get("elapsed_time"), data.get("duration")),
            moving_time=data.get("moving_time"),
            total_elevation_gain=_first(
                data.get("total_elevation_gain"), data.get("elevationGain")
            ),
            total_elevation_loss=data.get("total_elevation_loss"),
            trainer=data.get("trainer"),
            average_heartrate=_first(data.get("average_heartrate"), data.get("avgHr")),
            max_heartrate=data.get("max_heartrate"),
            average_cadence=data.get("average_cadence"),
            calories=data.get("calories"),
            average_speed=data.get("average_speed"),
            max_speed=data.get("max_speed"),
            average_temp=data.get("average_temp"),
            min_temp=data.get("min_temp"),
            max_temp=data.get("max_temp"),
            avg_lr_balance=data.get("avg_lr_balance"),
            perceived_exertion=data.get("perceived_exertion"),
            feel=data.get("feel"),
            session_rpe=data.get("session_rpe"),
            icu_ftp=data.get("icu_ftp"),
            icu_training_load=_first(
                data.get("icu_training_load"), data.get("trainingLoad")
            ),
            icu_atl=data.get("icu_atl"),
            icu_ctl=data.get("icu_ctl"),
            icu_average_watts=_first(
                data.get("icu_average_watts"),
                data.get("avgPower"),
                data.get("average_watts"),
            ),
            icu_weighted_avg_watts=data.get("icu_weighted_avg_watts"),
            icu_joules=data.get("icu_joules"),
            icu_intensity=data.get("icu_intensity"),
            icu_rpe=data.get("icu_rpe"),
            icu_power_hr=data.get("icu_power_hr"),
            icu_variability_index=data.get("icu_variability_index"),
            icu_resting_hr=data.get("icu_resting_hr"),
            icu_weight=data.get("icu_weight"),
            icu_efficiency_factor=data.get("icu_efficiency_factor"),
            lthr=data.get("lthr"),
            decoupling=data.get("decoupling"),
            average_stride=data.get("average_stride"),
            average_wind_speed=data.get("average_wind_speed"),
            headwind_percent=data.get("headwind_percent"),
            tailwind_percent=data.get("tailwind_percent"),
            trimp=data.get("trimp"),
            polarization_index=data.get("polarization_index"),
            power_load=data.get("power_load"),
            hr_load=data.get("hr_load"),
            pace_load=data.get("pace_load"),
            device_name=data.get("device_name"),
            power_meter=data.get("power_meter"),
            file_type=data.get("file_type"),
            tags=_normalize_tags(data.get("tags")),
        )


@dataclass(frozen=True)
class ActivityInterval:
    """A single interval from the icu_intervals array in the intervals response."""

    label: str | None = None
    type: str | None = None
    elapsed_time: int | None = None
    moving_time: int | None = None
    distance: float | None = None
    start_index: int | None = None
    end_index: int | None = None
    average_watts: int | None = None
    average_watts_kg: float | None = None
    max_watts: int | None = None
    max_watts_kg: float | None = None
    weighted_average_watts: int | None = None
    intensity: float | None = None
    training_load: float | None = None
    joules: int | None = None
    joules_above_ftp: int | None = None
    zone: int | None = None
    zone_min_watts: int | None = None
    zone_max_watts: int | None = None
    wbal_start: int | None = None
    wbal_end: int | None = None
    avg_lr_balance: float | None = None
    w5s_variability: float | None = None
    average_torque: float | None = None
    min_torque: float | None = None
    max_torque: float | None = None
    average_heartrate: int | None = None
    min_heartrate: int | None = None
    max_heartrate: int | None = None
    decoupling: float | None = None
    average_dfa_a1: float | None = None
    average_respiration: float | None = None
    average_epoc: float | None = None
    average_smo2: float | None = None
    average_smo2_2: float | None = None
    average_thb: float | None = None
    average_thb_2: float | None = None
    average_speed: float | None = None
    min_speed: float | None = None
    max_speed: float | None = None
    gap: float | None = None
    average_cadence: float | None = None
    min_cadence: int | None = None
    max_cadence: int | None = None
    average_stride: float | None = None
    total_elevation_gain: float | None = None
    min_altitude: float | None = None
    max_altitude: float | None = None
    average_gradient: float | None = None
    average_temp: float | None = None
    average_weather_temp: float | None = None
    average_feels_like: float | None = None
    average_wind_speed: float | None = None
    average_wind_gust: float | None = None
    prevailing_wind_deg: int | None = None
    headwind_percent: float | None = None
    tailwind_percent: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityInterval":
        """Create an ActivityInterval from a raw API response dict."""
        return cls(
            label=data.get("label"),
            type=data.get("type"),
            elapsed_time=data.get("elapsed_time"),
            moving_time=data.get("moving_time"),
            distance=data.get("distance"),
            start_index=data.get("start_index"),
            end_index=data.get("end_index"),
            average_watts=data.get("average_watts"),
            average_watts_kg=data.get("average_watts_kg"),
            max_watts=data.get("max_watts"),
            max_watts_kg=data.get("max_watts_kg"),
            weighted_average_watts=data.get("weighted_average_watts"),
            intensity=data.get("intensity"),
            training_load=data.get("training_load"),
            joules=data.get("joules"),
            joules_above_ftp=data.get("joules_above_ftp"),
            zone=data.get("zone"),
            zone_min_watts=data.get("zone_min_watts"),
            zone_max_watts=data.get("zone_max_watts"),
            wbal_start=data.get("wbal_start"),
            wbal_end=data.get("wbal_end"),
            avg_lr_balance=data.get("avg_lr_balance"),
            w5s_variability=data.get("w5s_variability"),
            average_torque=data.get("average_torque"),
            min_torque=data.get("min_torque"),
            max_torque=data.get("max_torque"),
            average_heartrate=data.get("average_heartrate"),
            min_heartrate=data.get("min_heartrate"),
            max_heartrate=data.get("max_heartrate"),
            decoupling=data.get("decoupling"),
            average_dfa_a1=data.get("average_dfa_a1"),
            average_respiration=data.get("average_respiration"),
            average_epoc=data.get("average_epoc"),
            average_smo2=data.get("average_smo2"),
            average_smo2_2=data.get("average_smo2_2"),
            average_thb=data.get("average_thb"),
            average_thb_2=data.get("average_thb_2"),
            average_speed=data.get("average_speed"),
            min_speed=data.get("min_speed"),
            max_speed=data.get("max_speed"),
            gap=data.get("gap"),
            average_cadence=data.get("average_cadence"),
            min_cadence=data.get("min_cadence"),
            max_cadence=data.get("max_cadence"),
            average_stride=data.get("average_stride"),
            total_elevation_gain=data.get("total_elevation_gain"),
            min_altitude=data.get("min_altitude"),
            max_altitude=data.get("max_altitude"),
            average_gradient=data.get("average_gradient"),
            average_temp=data.get("average_temp"),
            average_weather_temp=data.get("average_weather_temp"),
            average_feels_like=data.get("average_feels_like"),
            average_wind_speed=data.get("average_wind_speed"),
            average_wind_gust=data.get("average_wind_gust"),
            prevailing_wind_deg=data.get("prevailing_wind_deg"),
            headwind_percent=data.get("headwind_percent"),
            tailwind_percent=data.get("tailwind_percent"),
        )


@dataclass(frozen=True)
class ActivityIntervalGroup:
    """A group of intervals from the icu_groups array in the intervals response."""

    id: str | None = None
    count: int | None = None
    elapsed_time: int | None = None
    moving_time: int | None = None
    distance: float | None = None
    start_index: int | None = None
    average_watts: int | None = None
    average_watts_kg: float | None = None
    max_watts: int | None = None
    weighted_average_watts: int | None = None
    intensity: float | None = None
    average_heartrate: int | None = None
    max_heartrate: int | None = None
    average_speed: float | None = None
    max_speed: float | None = None
    average_cadence: float | None = None
    max_cadence: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityIntervalGroup":
        """Create an ActivityIntervalGroup from a raw API response dict."""
        return cls(
            id=data.get("id"),
            count=data.get("count"),
            elapsed_time=data.get("elapsed_time"),
            moving_time=data.get("moving_time"),
            distance=data.get("distance"),
            start_index=data.get("start_index"),
            average_watts=data.get("average_watts"),
            average_watts_kg=data.get("average_watts_kg"),
            max_watts=data.get("max_watts"),
            weighted_average_watts=data.get("weighted_average_watts"),
            intensity=data.get("intensity"),
            average_heartrate=data.get("average_heartrate"),
            max_heartrate=data.get("max_heartrate"),
            average_speed=data.get("average_speed"),
            max_speed=data.get("max_speed"),
            average_cadence=data.get("average_cadence"),
            max_cadence=data.get("max_cadence"),
        )


@dataclass(frozen=True)
class IntervalsData:
    """Top-level intervals response containing individual intervals and groups."""

    id: str | None = None
    analyzed: Any = None
    icu_intervals: list[ActivityInterval] = field(default_factory=list)
    icu_groups: list[ActivityIntervalGroup] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntervalsData":
        """Create an IntervalsData from a raw API response dict."""
        return cls(
            id=data.get("id"),
            analyzed=data.get("analyzed"),
            icu_intervals=[
                ActivityInterval.from_dict(i)
                for i in _dict_items(data.get("icu_intervals") or [], "icu_intervals")
            ],
            icu_groups=[
                ActivityIntervalGroup.from_dict(g)
                for g in _dict_items(data.get("icu_groups") or [], "icu_groups")
            ],
        )


@dataclass(frozen=True)
class ActivityMessage:
    """A message or note attached to an activity."""

    name: str | None = None
    created: str | None = None
    type: str | None = None
    content: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityMessage":
        """Create an ActivityMessage from a raw API response dict."""
        return cls(
            name=data.get("name"),
            created=data.get("created"),
            type=data.get("type"),
            content=data.get("content"),
        )


@dataclass(frozen=True)
class WellnessSportInfo:
    """Sport-specific info entry nested inside a WellnessEntry."""

    type: str | None = None
    eftp: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WellnessSportInfo":
        """Create a WellnessSportInfo from a raw API response dict."""
        return cls(type=data.get("type"), eftp=data.get("eftp"))


@dataclass(frozen=True)
class WellnessEntry:
    """Wellness data entry for a single day."""

    id: str | None = None
    ctl: float | None = None
    atl: float | None = None
    ramp_rate: float | None = None
    ctl_load: float | None = None
    atl_load: float | None = None
    sport_info: list[WellnessSportInfo] = field(default_factory=list)
    weight: float | None = None
    resting_hr: int | None = None
    hrv: float | None = None
    hrv_sdnn: float | None = None
    menstrual_phase: str | None = None
    menstrual_phase_predicted: str | None = None
    kcal_consumed: int | None = None
    sleep_secs: int | None = None
    sleep_score: float | None = None
    sleep_quality: int | None = None
    avg_sleeping_hr: float | None = None
    soreness: int | None = None
    fatigue: int | None = None
    stress: int | None = None
    mood: int | None = None
    motivation: int | None = None
    injury: int | None = None
    spo2: float | None = None
    systolic: int | None = None
    diastolic: int | None = None
    hydration: int | None = None
    hydration_volume: float | None = None
    readiness: float | None = None
    baevsky_si: float | None = None
    blood_glucose: float | None = None
    lactate: float | None = None
    body_fat: float | None = None
    abdomen: float | None = None
    vo2max: float | None = None
    comments: str | None = None
    steps: int | None = None
    respiration: float | None = None
    locked: bool | None = None
    sleep_hours: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WellnessEntry":
        """Create a WellnessEntry from a raw API response dict."""
        return cls(
            id=data.get("id"),
            ctl=data.get("ctl"),
            atl=data.get("atl"),
            ramp_rate=data.get("rampRate"),
            ctl_load=data.get("ctlLoad"),
            atl_load=data.get("atlLoad"),
            sport_info=[
                WellnessSportInfo.from_dict(s)
                for s in _dict_items(data.get("sportInfo") or [], "sportInfo")
            ],
            weight=data.get("weight"),
            resting_hr=_first(data.get("restingHR"), data.get("restingHr")),
            hrv=data.get("hrv"),
            hrv_sdnn=data.get("hrvSDNN"),
            menstrual_phase=_safe_enum(MenstrualPhase, data.get("menstrualPhase")),
            menstrual_phase_predicted=_safe_enum(MenstrualPhase, data.get("menstrualPhasePredicted")),
            kcal_consumed=data.get("kcalConsumed"),
            sleep_secs=data.get("sleepSecs"),
            sleep_score=data.get("sleepScore"),
            sleep_quality=data.get("sleepQuality"),
            avg_sleeping_hr=data.get("avgSleepingHR"),
            soreness=data.get("soreness"),
            fatigue=data.get("fatigue"),
            stress=data.get("stress"),
            mood=data.get("mood"),
            motivation=data.get("motivation"),
            injury=data.get("injury"),
            spo2=data.get("spO2"),
            systolic=data.get("systolic"),
            diastolic=data.get("diastolic"),
            hydration=data.get("hydration"),
            hydration_volume=data.get("hydrationVolume"),
            readiness=data.get("readiness"),
            baevsky_si=data.get("baevskySI"),
            blood_glucose=data.get("bloodGlucose"),
            lactate=data.get("lactate"),
            body_fat=data.get("bodyFat"),
            abdomen=data.get("abdomen"),
            vo2max=data.get("vo2max"),
            comments=data.get("comments"),
            steps=data.get("steps"),
            respiration=data.get("respiration"),
            locked=data.get("locked"),
            sleep_hours=data.get("sleepHours"),
        )


@dataclass(frozen=True)
class Athlete:
    """Athlete profile — fields used by the get_athlete tool and formatter."""

    id: str | None = None
    name: str | None = None
    weight: float | None = None
    icu_resting_hr: int | None = None
    location: str | None = None
    timezone: str | None = None
    status: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Athlete":
        """Create an Athlete from a raw API response dict."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            weight=_first(data.get("weight"), data.get("icu_weight")),
            icu_resting_hr=_first(
                data.get("icu_resting_hr"),
                data.get("restingHr"),
                data.get("resting_hr"),
            ),
            location=data.get("location") or data.get("city"),
            timezone=data.get("timezone"),
            status=_safe_enum(AthleteStatus, data.get("status")),
        )


@dataclass(frozen=True)
class AthleteSportSettings:
    """Athlete sport settings — FTP, zones, LTHR, pacing, warmup/cooldown."""

    type: str | None = None
    ftp: int | None = None
    lthr: int | None = None
    max_hr: int | None = None
    power_zones: list[int] = field(default_factory=list)
    hr_zones: list[int] = field(default_factory=list)
    pace_zones: list[float] = field(default_factory=list)
    warmup_time: int | None = None
    cooldown_time: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AthleteSportSettings":
        """Create an AthleteSportSettings from a raw API response dict."""
        return cls(
            type=_safe_enum(SportType, data.get("type")),
            ftp=data.get("ftp"),
            lthr=data.get("lthr"),
            max_hr=_first(data.get("max_hr"), data.get("maxHr")),
            power_zones=_get_list(data, "power_zones", "zones", "powerZones"),
            hr_zones=_get_list(data, "hr_zones"),
            pace_zones=_get_list(data, "pace_zones", "paceZones"),
            warmup_time=_first(data.get("warmup_time"), data.get("warmup")),
            cooldown_time=_first(data.get("cooldown_time"), data.get("cooldown")),
        )


@dataclass
class CustomItem:
    """Custom item (chart, field, zone, etc.) from the Intervals.icu API."""

    id: int | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    visibility: str | None = None
    index: int | None = None
    hide_script: bool | None = None
    content: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomItem":
        """Create a CustomItem from a raw API response dict."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            type=_safe_enum(CustomItemType, data.get("type")),
            description=data.get("description"),
            visibility=_safe_enum(CustomItemVisibility, data.get("visibility")),
            index=data.get("index"),
            hide_script=data.get("hide_script"),
            content=data.get("content"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API request bodies, including only API-accepted fields and omitting None values."""
        data: dict[str, Any] = {}
        if self.name is not None:
            data["name"] = self.name
        if self.type is not None:
            data["type"] = self.type
        if self.description is not None:
            data["description"] = self.description
        if self.visibility is not None:
            data["visibility"] = self.visibility
        if self.content is not None:
            data["content"] = self.content
        return data


@dataclass
class Workout:
    """Library workout from the Intervals.icu API."""

    id: int | None = None
    athlete_id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    folder_id: int | None = None
    tags: list[str] = field(default_factory=list)
    indoor: bool | None = None
    distance: float | None = None
    color: str | None = None
    moving_time: int | None = None
    icu_training_load: int | None = None
    target: str | None = None
    workout_doc: WorkoutDoc | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workout":
        """Create a Workout from a raw API response dict."""
        raw_doc = _first(data.get("workout_doc"), data.get("workoutDoc"))
        return cls(
            id=data.get("id"),
            athlete_id=data.get("athlete_id"),
            name=data.get("name"),
            description=data.get("description"),
            type=_safe_enum(SportType, data.get("type")),
            folder_id=_first(data.get("folder_id"), data.get("folderId")),
            tags=_normalize_tags(data.get("tags")),
            indoor=data.get("indoor"),
            distance=data.get("distance"),
            color=data.get("color"),
            moving_time=_first(data.get("moving_time"), data.get("duration")),
            icu_training_load=_first(data.get("icu_training_load"), data.get("tss")),
            target=data.get("target"),
            workout_doc=WorkoutDoc.from_dict(raw_doc) if isinstance(raw_doc, dict) else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for API request bodies, including only API-accepted fields and omitting None values."""
        data: dict[str, Any] = {}
        if self.name is not None:
            data["name"] = self.name
        if self.description is not None:
            data["description"] = self.description
        if self.type is not None:
            data["type"] = self.type
        if self.folder_id is not None:
            data["folder_id"] = self.folder_id
        if self.tags:
            data["tags"] = self.tags
        if self.indoor is not None:
            data["indoor"] = self.indoor
        if self.distance is not None:
            data["distance"] = self.distance
        if self.color is not None:
            data["color"] = self.color
        if self.moving_time is not None:
            data["moving_time"] = self.moving_time
        if self.icu_training_load is not None:
            data["icu_training_load"] = self.icu_training_load
        if self.target is not None:
            data["target"] = self.target
        if self.workout_doc is not None:
            data["workout_doc"] = self.workout_doc.to_dict()
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


@dataclass(frozen=True)
class Folder:
    """Workout folder from the Intervals.icu API."""

    id: int | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None
    workouts: list[Workout] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Folder":
        """Create a Folder from a raw API response dict."""
        raw_workouts = data.get("workouts") or data.get("children") or []
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            type=data.get("type"),
            description=data.get("description"),
            workouts=[
                Workout.from_dict(w) for w in _dict_items(raw_workouts, "workouts")
            ],
        )


@dataclass(frozen=True)
class EventWorkout:
    """Nested workout object inside an event response (EventEx)."""

    id: int | None = None
    type: str | None = None
    moving_time: int | None = None
    icu_training_load: int | None = None
    intervals: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventWorkout":
        """Create an EventWorkout from a raw API response dict."""
        return cls(
            id=data.get("id"),
            type=data.get("type"),
            moving_time=_first(data.get("moving_time"), data.get("duration")),
            icu_training_load=_first(
                data.get("icu_training_load"), data.get("tss")
            ),
            intervals=_dict_items(data.get("intervals") or [], "intervals"),
        )


@dataclass(frozen=True)
class EventResponse:
    """Event response from the Intervals.icu API (Event / EventEx)."""

    id: int | None = None
    start_date_local: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    category: str | None = None
    race: bool | None = None
    priority: str | None = None
    result: str | None = None
    workout: EventWorkout | None = None
    calendar: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventResponse":
        """Create an EventResponse from a raw API response dict."""
        workout_data = data.get("workout")
        return cls(
            id=data.get("id"),
            start_date_local=_first(
                data.get("start_date_local"), data.get("date")
            ),
            name=data.get("name"),
            description=data.get("description"),
            type=_safe_enum(SportType, data.get("type")),
            category=_safe_enum(EventCategory, data.get("category")),
            race=data.get("race"),
            priority=data.get("priority"),
            result=data.get("result"),
            workout=(
                EventWorkout.from_dict(workout_data)
                if isinstance(workout_data, dict)
                else None
            ),
            calendar=data.get("calendar"),
        )


@dataclass
class EventRequest:
    """Request body for creating or updating an event."""

    start_date_local: str
    name: str
    category: str = EventCategory.WORKOUT
    type: str = "Ride"
    description: str | None = None
    moving_time: int | None = None
    distance: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for the API request body, omitting None values."""
        data: dict[str, Any] = {
            "start_date_local": self.start_date_local,
            "category": self.category,
            "name": self.name,
            "type": self.type,
        }
        if self.description is not None:
            data["description"] = self.description
        if self.moving_time is not None:
            data["moving_time"] = self.moving_time
        if self.distance is not None:
            data["distance"] = self.distance
        return data
