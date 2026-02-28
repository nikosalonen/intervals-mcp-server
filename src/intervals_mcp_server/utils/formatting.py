"""
Formatting utilities for Intervals.icu MCP Server

This module contains formatting functions for handling data from the Intervals.icu API.
"""

import json
import logging
from datetime import datetime
from typing import Any

from intervals_mcp_server.utils.schemas import (
    Activity,
    ActivityMessage,
    Athlete,
    AthleteSportSettings,
    CustomItem,
    EventResponse,
    EventWorkout,
    Folder,
    IntervalsData,
    WellnessEntry,
    Workout,
)

logger = logging.getLogger(__name__)


def _fmt(val: Any, default: str = "N/A") -> Any:
    """Return val if not None, otherwise return default."""
    return default if val is None else val


def _fmt_datetime(value: str | None) -> str:
    """Parse and format an ISO datetime string to YYYY-MM-DD HH:MM:SS."""
    if not value:
        return "Unknown"
    if len(value) > 10:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            logger.warning("Failed to parse datetime: %s", value)
    return value


def format_activity_summary(activity: Activity) -> str:
    """Format an activity into a readable string."""
    start_time = _fmt_datetime(activity.start_date)

    rpe = activity.perceived_exertion
    if rpe is None:
        rpe = activity.icu_rpe
    rpe_str = f"{rpe}/10" if isinstance(rpe, (int, float)) else _fmt(rpe)

    feel_str = f"{activity.feel}/5" if activity.feel is not None else "N/A"

    return f"""
Activity: {_fmt(activity.name, "Unnamed")}
ID: {_fmt(activity.id)}
Type: {_fmt(activity.type, "Unknown")}
Date: {start_time}
Description: {_fmt(activity.description)}
Distance: {activity.distance or 0} meters
Duration: {activity.elapsed_time or 0} seconds
Moving Time: {_fmt(activity.moving_time)} seconds
Elevation Gain: {activity.total_elevation_gain or 0} meters
Elevation Loss: {_fmt(activity.total_elevation_loss)} meters

Power Data:
Average Power: {_fmt(activity.icu_average_watts)} watts
Weighted Avg Power: {_fmt(activity.icu_weighted_avg_watts)} watts
Training Load: {_fmt(activity.icu_training_load)}
FTP: {_fmt(activity.icu_ftp)} watts
Kilojoules: {_fmt(activity.icu_joules)}
Intensity: {_fmt(activity.icu_intensity)}
Power:HR Ratio: {_fmt(activity.icu_power_hr)}
Variability Index: {_fmt(activity.icu_variability_index)}

Heart Rate Data:
Average Heart Rate: {_fmt(activity.average_heartrate)} bpm
Max Heart Rate: {_fmt(activity.max_heartrate)} bpm
LTHR: {_fmt(activity.lthr)} bpm
Resting HR: {_fmt(activity.icu_resting_hr)} bpm
Decoupling: {_fmt(activity.decoupling)}

Other Metrics:
Cadence: {_fmt(activity.average_cadence)} rpm
Calories: {_fmt(activity.calories)}
Average Speed: {_fmt(activity.average_speed)} m/s
Max Speed: {_fmt(activity.max_speed)} m/s
Average Stride: {_fmt(activity.average_stride)}
L/R Balance: {_fmt(activity.avg_lr_balance)}
Weight: {_fmt(activity.icu_weight)} kg
RPE: {rpe_str}
Session RPE: {_fmt(activity.session_rpe)}
Feel: {feel_str}

Environment:
Trainer: {_fmt(activity.trainer)}
Average Temp: {_fmt(activity.average_temp)}°C
Min Temp: {_fmt(activity.min_temp)}°C
Max Temp: {_fmt(activity.max_temp)}°C
Avg Wind Speed: {_fmt(activity.average_wind_speed)} km/h
Headwind %: {_fmt(activity.headwind_percent)}%
Tailwind %: {_fmt(activity.tailwind_percent)}%

Training Metrics:
Fitness (CTL): {_fmt(activity.icu_ctl)}
Fatigue (ATL): {_fmt(activity.icu_atl)}
TRIMP: {_fmt(activity.trimp)}
Polarization Index: {_fmt(activity.polarization_index)}
Power Load: {_fmt(activity.power_load)}
HR Load: {_fmt(activity.hr_load)}
Pace Load: {_fmt(activity.pace_load)}
Efficiency Factor: {_fmt(activity.icu_efficiency_factor)}

Device Info:
Device: {_fmt(activity.device_name)}
Power Meter: {_fmt(activity.power_meter)}
File Type: {_fmt(activity.file_type)}
"""


def format_workout(workout: Workout) -> str:
    """Format a workout into a readable string."""
    return f"""
Workout: {_fmt(workout.name, "Unnamed")}
ID: {_fmt(workout.id)}
Description: {_fmt(workout.description, "No description")}
Sport: {_fmt(workout.type, "Unknown")}
Folder ID: {_fmt(workout.folder_id)}
Tags: {_fmt(", ".join(str(t) for t in workout.tags if t is not None) if workout.tags else None)}
Indoor: {_fmt(workout.indoor)}
Distance: {_fmt(workout.distance)}
Color: {_fmt(workout.color)}
Duration: {workout.moving_time or 0} seconds
TSS: {_fmt(workout.icu_training_load)}
"""


def _format_training_metrics(entry: WellnessEntry) -> list[str]:
    """Format training metrics section."""
    training_metrics = []
    for value, label in [
        (entry.ctl, "Fitness (CTL)"),
        (entry.atl, "Fatigue (ATL)"),
        (entry.ramp_rate, "Ramp Rate"),
        (entry.ctl_load, "CTL Load"),
        (entry.atl_load, "ATL Load"),
    ]:
        if value is not None:
            training_metrics.append(f"- {label}: {value}")
    return training_metrics


def _format_sport_info(entry: WellnessEntry) -> list[str]:
    """Format sport-specific info section."""
    sport_info_list = []
    for sport in entry.sport_info:
        if sport.eftp is not None:
            sport_info_list.append(f"- {sport.type}: eFTP = {sport.eftp}")
    return sport_info_list


def _format_vital_signs(entry: WellnessEntry) -> list[str]:
    """Format vital signs section."""
    vital_signs = []
    for value, label, unit in [
        (entry.weight, "Weight", "kg"),
        (entry.resting_hr, "Resting HR", "bpm"),
        (entry.hrv, "HRV", ""),
        (entry.hrv_sdnn, "HRV SDNN", ""),
        (entry.avg_sleeping_hr, "Average Sleeping HR", "bpm"),
        (entry.spo2, "SpO2", "%"),
        (entry.respiration, "Respiration", "breaths/min"),
        (entry.blood_glucose, "Blood Glucose", "mmol/L"),
        (entry.lactate, "Lactate", "mmol/L"),
        (entry.vo2max, "VO2 Max", "ml/kg/min"),
        (entry.body_fat, "Body Fat", "%"),
        (entry.abdomen, "Abdomen", "cm"),
        (entry.baevsky_si, "Baevsky Stress Index", ""),
    ]:
        if value is not None:
            vital_signs.append(f"- {label}: {value}{(' ' + unit) if unit else ''}")

    if entry.systolic is not None and entry.diastolic is not None:
        vital_signs.append(f"- Blood Pressure: {entry.systolic}/{entry.diastolic} mmHg")
    elif entry.systolic is not None:
        vital_signs.append(f"- Systolic BP: {entry.systolic}")

    return vital_signs


def _format_sleep_recovery(entry: WellnessEntry) -> list[str]:
    """Format sleep and recovery section."""
    sleep_lines = []
    sleep_hours = None
    if entry.sleep_secs is not None:
        sleep_hours = f"{entry.sleep_secs / 3600:.2f}"
    elif entry.sleep_hours is not None:
        sleep_hours = f"{entry.sleep_hours}"
    if sleep_hours is not None:
        sleep_lines.append(f"  Sleep: {sleep_hours} hours")

    if entry.sleep_quality is not None:
        quality_labels = {1: "Great", 2: "Good", 3: "Average", 4: "Poor"}
        quality_text = quality_labels.get(entry.sleep_quality, str(entry.sleep_quality))
        sleep_lines.append(f"  Sleep Quality: {entry.sleep_quality} ({quality_text})")

    if entry.sleep_score is not None:
        sleep_lines.append(f"  Device Sleep Score: {entry.sleep_score}/100")

    if entry.readiness is not None:
        sleep_lines.append(f"  Readiness: {entry.readiness}/10")

    return sleep_lines


def _format_menstrual_tracking(entry: WellnessEntry) -> list[str]:
    """Format menstrual tracking section."""
    menstrual_lines = []
    if entry.menstrual_phase is not None:
        menstrual_lines.append(f"  Menstrual Phase: {str(entry.menstrual_phase).capitalize()}")
    if entry.menstrual_phase_predicted is not None:
        menstrual_lines.append(
            f"  Predicted Phase: {str(entry.menstrual_phase_predicted).capitalize()}"
        )
    return menstrual_lines


def _format_subjective_feelings(entry: WellnessEntry) -> list[str]:
    """Format subjective feelings section."""
    subjective_lines = []
    for value, label in [
        (entry.soreness, "Soreness"),
        (entry.fatigue, "Fatigue"),
        (entry.stress, "Stress"),
        (entry.mood, "Mood"),
        (entry.motivation, "Motivation"),
        (entry.injury, "Injury Level"),
    ]:
        if value is not None:
            subjective_lines.append(f"  {label}: {value}/10")
    return subjective_lines


def _format_nutrition_hydration(entry: WellnessEntry) -> list[str]:
    """Format nutrition and hydration section."""
    nutrition_lines = []
    for value, label in [
        (entry.kcal_consumed, "Calories Consumed"),
        (entry.hydration_volume, "Hydration Volume"),
    ]:
        if value is not None:
            nutrition_lines.append(f"- {label}: {value}")

    if entry.hydration is not None:
        nutrition_lines.append(f"  Hydration Score: {entry.hydration}/10")

    return nutrition_lines


def format_wellness_entry(entry: WellnessEntry) -> str:
    """Format wellness entry data into a readable string.

    Formats various wellness metrics including training metrics, vital signs,
    sleep data, menstrual tracking, subjective feelings, nutrition, and daily steps.

    Args:
        entry: WellnessEntry containing wellness data for a single day.

    Returns:
        A formatted string representation of the wellness entry.
    """
    lines = ["Wellness Data:"]
    lines.append(f"Date: {_fmt(entry.id)}")
    lines.append("")

    training_metrics = _format_training_metrics(entry)
    if training_metrics:
        lines.append("Training Metrics:")
        lines.extend(training_metrics)
        lines.append("")

    sport_info_list = _format_sport_info(entry)
    if sport_info_list:
        lines.append("Sport-Specific Info:")
        lines.extend(sport_info_list)
        lines.append("")

    vital_signs = _format_vital_signs(entry)
    if vital_signs:
        lines.append("Vital Signs:")
        lines.extend(vital_signs)
        lines.append("")

    sleep_lines = _format_sleep_recovery(entry)
    if sleep_lines:
        lines.append("Sleep & Recovery:")
        lines.extend(sleep_lines)
        lines.append("")

    menstrual_lines = _format_menstrual_tracking(entry)
    if menstrual_lines:
        lines.append("Menstrual Tracking:")
        lines.extend(menstrual_lines)
        lines.append("")

    subjective_lines = _format_subjective_feelings(entry)
    if subjective_lines:
        lines.append("Subjective Feelings:")
        lines.extend(subjective_lines)
        lines.append("")

    nutrition_lines = _format_nutrition_hydration(entry)
    if nutrition_lines:
        lines.append("Nutrition & Hydration:")
        lines.extend(nutrition_lines)
        lines.append("")

    if entry.steps is not None:
        lines.append("Activity:")
        lines.append(f"- Steps: {entry.steps}")
        lines.append("")

    if entry.comments:
        lines.append(f"Comments: {entry.comments}")
    if entry.locked is not None:
        lines.append(f"Status: {'Locked' if entry.locked else 'Unlocked'}")

    return "\n".join(lines)


def format_event_summary(event: EventResponse) -> str:
    """Format a basic event summary into a readable string."""
    event_type = "Workout" if event.workout else "Race" if event.race else "Other"
    return f"""Date: {_fmt(event.start_date_local, "Unknown")}
ID: {_fmt(event.id)}
Type: {event_type}
Name: {_fmt(event.name, "Unnamed")}
Description: {_fmt(event.description, "No description")}"""


def format_event_details(event: EventResponse) -> str:
    """Format detailed event information into a readable string."""
    event_details = f"""Event Details:

ID: {_fmt(event.id)}
Date: {_fmt(event.start_date_local, "Unknown")}
Name: {_fmt(event.name, "Unnamed")}
Description: {_fmt(event.description, "No description")}"""

    if event.workout is not None:
        workout: EventWorkout = event.workout
        event_details += f"""

Workout Information:
Workout ID: {_fmt(workout.id)}
Sport: {_fmt(workout.type, "Unknown")}
Duration: {workout.moving_time or 0} seconds
TSS: {_fmt(workout.icu_training_load)}"""

        if workout.intervals:
            event_details += f"\nIntervals: {len(workout.intervals)}"

    if event.race:
        event_details += f"""

Race Information:
Priority: {_fmt(event.priority)}
Result: {_fmt(event.result)}"""

    if event.calendar is not None:
        if isinstance(event.calendar, dict):
            event_details += f"\n\nCalendar: {_fmt(event.calendar.get('name'))}"
        else:
            event_details += f"\n\nCalendar: {_fmt(event.calendar)}"

    return event_details


def format_activity_message(message: ActivityMessage) -> str:
    """Format an activity message/note into a readable string."""
    created = _fmt_datetime(message.created)
    return f"""Author: {_fmt(message.name, "Unknown")}
Date: {created}
Type: {_fmt(message.type, "TEXT")}
Content: {message.content or ""}"""


def format_custom_item_details(item: CustomItem) -> str:
    """Format detailed custom item information into a readable string."""
    lines = ["Custom Item Details:", ""]
    lines.append(f"ID: {_fmt(item.id)}")
    lines.append(f"Name: {_fmt(item.name)}")
    lines.append(f"Type: {_fmt(item.type)}")

    if item.description:
        lines.append(f"Description: {item.description}")
    if item.visibility:
        lines.append(f"Visibility: {item.visibility}")
    if item.index is not None:
        lines.append(f"Index: {item.index}")
    if item.hide_script is not None:
        lines.append(f"Hide Script: {item.hide_script}")
    if item.content:
        lines.append(f"Content: {json.dumps(item.content, indent=2)}")

    return "\n".join(lines)


def format_athlete_summary(athlete: Athlete) -> str:
    """Format athlete profile into a readable string."""
    return f"""Athlete: {_fmt(athlete.name)}
ID: {_fmt(athlete.id)}
Weight: {_fmt(athlete.weight)} kg
Resting HR: {_fmt(athlete.icu_resting_hr)} bpm
Location: {_fmt(athlete.location)}
Timezone: {_fmt(athlete.timezone)}
Status: {_fmt(athlete.status)}"""


def format_sport_settings(setting: AthleteSportSettings) -> str:
    """Format sport settings into a readable string."""
    lines = [
        f"Sport: {_fmt(setting.type)}",
        f"FTP: {_fmt(setting.ftp)}",
        f"LTHR: {_fmt(setting.lthr)}",
        f"Max HR: {_fmt(setting.max_hr)}",
        f"Pace zones: {setting.pace_zones or 'N/A'}",
        f"Warmup: {_fmt(setting.warmup_time)} s",
        f"Cooldown: {_fmt(setting.cooldown_time)} s",
    ]
    if setting.power_zones:
        lines.append(f"Power zones: {setting.power_zones}")
    if setting.hr_zones:
        lines.append(f"HR zones: {setting.hr_zones}")
    return "\n".join(lines)


def format_search_result(result: Activity) -> str:
    """Format a lightweight activity search result."""
    start = _fmt_datetime(result.start_date) if result.start_date else "N/A"
    tags_str = ", ".join(str(t) for t in result.tags if t is not None) if result.tags else "none"
    return (
        f"ID: {_fmt(result.id)} | {_fmt(result.name, 'Unnamed')} | "
        f"{start} | {_fmt(result.type)} | {result.distance or 0} m | Tags: {tags_str}"
    )


def format_folder_summary(folder: Folder) -> str:
    """Format workout folder summary."""
    lines = [
        f"Folder: {_fmt(folder.name)}",
        f"ID: {_fmt(folder.id)}",
        f"Workouts: {len(folder.workouts)}",
    ]
    for w in folder.workouts:
        if w.name:
            lines.append(f"- {w.name}")
    return "\n".join(lines)


def format_intervals(intervals_data: IntervalsData) -> str:
    """Format intervals data into a readable string with all available fields.

    Args:
        intervals_data: Parsed IntervalsData from the Intervals.icu API.

    Returns:
        A formatted string representation of the intervals data.
    """
    parts = [
        f"Intervals Analysis:\n\nID: {_fmt(intervals_data.id)}\nAnalyzed: {_fmt(intervals_data.analyzed)}\n\n"
    ]

    if intervals_data.icu_intervals:
        parts.append("Individual Intervals:\n\n")

        for i, interval in enumerate(intervals_data.icu_intervals, 1):
            label = interval.label or f"Interval {i}"
            itype = interval.type or "Unknown"
            parts.append(
                f"[{i}] {label} ({itype})\n"
                f"Duration: {interval.elapsed_time or 0} seconds (moving: {interval.moving_time or 0} seconds)\n"
                f"Distance: {interval.distance or 0} meters\n"
                f"Start-End Indices: {interval.start_index or 0}-{interval.end_index or 0}\n"
                f"\nPower Metrics:\n"
                f"  Average Power: {interval.average_watts or 0} watts ({interval.average_watts_kg or 0} W/kg)\n"
                f"  Max Power: {interval.max_watts or 0} watts ({interval.max_watts_kg or 0} W/kg)\n"
                f"  Weighted Avg Power: {interval.weighted_average_watts or 0} watts\n"
                f"  Intensity: {interval.intensity or 0}\n"
                f"  Training Load: {interval.training_load or 0}\n"
                f"  Joules: {interval.joules or 0}\n"
                f"  Joules > FTP: {interval.joules_above_ftp or 0}\n"
                f"  Power Zone: {_fmt(interval.zone)} ({interval.zone_min_watts or 0}-{interval.zone_max_watts or 0} watts)\n"
                f"  W' Balance: Start {interval.wbal_start or 0}, End {interval.wbal_end or 0}\n"
                f"  L/R Balance: {interval.avg_lr_balance or 0}\n"
                f"  Variability: {interval.w5s_variability or 0}\n"
                f"  Torque: Avg {interval.average_torque or 0}, Min {interval.min_torque or 0}, Max {interval.max_torque or 0}\n"
                f"\nHeart Rate & Metabolic:\n"
                f"  Heart Rate: Avg {interval.average_heartrate or 0}, Min {interval.min_heartrate or 0}, Max {interval.max_heartrate or 0} bpm\n"
                f"  Decoupling: {interval.decoupling or 0}\n"
                f"  DFA α1: {interval.average_dfa_a1 or 0}\n"
                f"  Respiration: {interval.average_respiration or 0} breaths/min\n"
                f"  EPOC: {interval.average_epoc or 0}\n"
                f"  SmO2: {interval.average_smo2 or 0}% / {interval.average_smo2_2 or 0}%\n"
                f"  THb: {interval.average_thb or 0} / {interval.average_thb_2 or 0}\n"
                f"\nSpeed & Cadence:\n"
                f"  Speed: Avg {interval.average_speed or 0}, Min {interval.min_speed or 0}, Max {interval.max_speed or 0} m/s\n"
                f"  GAP: {interval.gap or 0} m/s\n"
                f"  Cadence: Avg {interval.average_cadence or 0}, Min {interval.min_cadence or 0}, Max {interval.max_cadence or 0} rpm\n"
                f"  Stride: {interval.average_stride or 0}\n"
                f"\nElevation & Environment:\n"
                f"  Elevation Gain: {interval.total_elevation_gain or 0} meters\n"
                f"  Altitude: Min {interval.min_altitude or 0}, Max {interval.max_altitude or 0} meters\n"
                f"  Gradient: {interval.average_gradient or 0}%\n"
                f"  Temperature: {interval.average_temp or 0}°C (Weather: {interval.average_weather_temp or 0}°C, Feels like: {interval.average_feels_like or 0}°C)\n"
                f"  Wind: Speed {interval.average_wind_speed or 0} km/h, Gust {interval.average_wind_gust or 0} km/h, Direction {interval.prevailing_wind_deg or 0}°\n"
                f"  Headwind: {interval.headwind_percent or 0}%, Tailwind: {interval.tailwind_percent or 0}%\n\n"
            )

    if intervals_data.icu_groups:
        parts.append("Interval Groups:\n\n")

        for i, group in enumerate(intervals_data.icu_groups, 1):
            parts.append(
                f"Group: {_fmt(group.id, f'Group {i}')} (Contains {group.count or 0} intervals)\n"
                f"Duration: {group.elapsed_time or 0} seconds (moving: {group.moving_time or 0} seconds)\n"
                f"Distance: {group.distance or 0} meters\n"
                f"Start-End Indices: {group.start_index or 0}-N/A\n\n"
                f"Power: Avg {group.average_watts or 0} watts ({group.average_watts_kg or 0} W/kg), Max {group.max_watts or 0} watts\n"
                f"W. Avg Power: {group.weighted_average_watts or 0} watts, Intensity: {group.intensity or 0}\n"
                f"Heart Rate: Avg {group.average_heartrate or 0}, Max {group.max_heartrate or 0} bpm\n"
                f"Speed: Avg {group.average_speed or 0}, Max {group.max_speed or 0} m/s\n"
                f"Cadence: Avg {group.average_cadence or 0}, Max {group.max_cadence or 0} rpm\n\n"
            )

    return "".join(parts)
