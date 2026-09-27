"""
Configuration management for Intervals.icu MCP Server.

This module handles loading and validation of configuration from environment variables.
"""

import logging
import os
from dataclasses import dataclass
from typing import Literal, cast

from intervals_mcp_server.utils.validation import validate_athlete_id

# Try to load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv

    _ = load_dotenv()
except ImportError:
    # python-dotenv not installed, proceed without it
    pass

logger = logging.getLogger("intervals_icu_mcp_server")

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVELS: tuple[LogLevel, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
DEFAULT_LOG_LEVEL: LogLevel = "INFO"

# Accepted by Python's own logging module, so operators reasonably expect them here.
LOG_LEVEL_ALIASES: dict[str, LogLevel] = {"WARN": "WARNING", "FATAL": "CRITICAL"}


def resolve_log_level() -> LogLevel:
    """
    Resolve the MCP server log level from FASTMCP_LOG_LEVEL.

    Accepts any case, tolerates surrounding whitespace, and maps the aliases
    WARN and FATAL. An unrecognised value degrades to INFO with a warning rather
    than raising: `mcp_instance` builds the MCPServer at module level, so the
    level has to be known at import time, and raising there would make a log
    verbosity typo break every import path -- pytest collection included.

    Returns:
        LogLevel: The configured level, defaulting to INFO.
    """
    raw = os.getenv("FASTMCP_LOG_LEVEL")
    if raw is None:
        return DEFAULT_LOG_LEVEL

    level = raw.strip().upper()
    level = LOG_LEVEL_ALIASES.get(level, cast(LogLevel, level))

    if level not in LOG_LEVELS:
        logger.warning(
            "Unsupported FASTMCP_LOG_LEVEL value %r; falling back to %s. Use one of: %s.",
            raw,
            DEFAULT_LOG_LEVEL,
            ", ".join(LOG_LEVELS),
        )
        return DEFAULT_LOG_LEVEL

    return cast(LogLevel, level)


@dataclass
class Config:
    """Configuration settings for the Intervals.icu MCP Server."""

    api_key: str
    athlete_id: str
    intervals_api_base_url: str
    user_agent: str


_config_instance: Config | None = None


def load_config() -> Config:
    """
    Load configuration from environment variables.

    Returns:
        Config: Configuration instance with loaded values.

    Raises:
        ValueError: If athlete_id is invalid (when non-empty).
    """
    api_key = os.getenv("API_KEY", "")
    athlete_id = os.getenv("ATHLETE_ID", "")
    intervals_api_base_url = os.getenv("INTERVALS_API_BASE_URL", "https://intervals.icu/api/v1")
    user_agent = "intervalsicu-mcp-server/1.0"

    # Validate athlete_id if provided (empty string is allowed)
    if athlete_id:
        validate_athlete_id(athlete_id)

    return Config(
        api_key=api_key,
        athlete_id=athlete_id,
        intervals_api_base_url=intervals_api_base_url,
        user_agent=user_agent,
    )


def get_config() -> Config:
    """
    Get the configuration instance (singleton pattern).

    Returns:
        Config: The configuration instance.
    """
    global _config_instance  # pylint: disable=global-statement  # noqa: PLW0603 - singleton pattern
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance
