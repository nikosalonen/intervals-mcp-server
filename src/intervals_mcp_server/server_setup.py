"""
Server setup and initialization for Intervals.icu MCP Server.

This module handles transport configuration and server startup logic.
"""

import os
import logging
from typing import Literal, cast

from mcp.server.mcpserver import MCPServer  # pylint: disable=import-error

from intervals_mcp_server.utils.types import TransportAliases

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVELS: tuple[LogLevel, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

logger = logging.getLogger("intervals_icu_mcp_server")

# MCP SDK v2 dropped pydantic-settings and reads no environment of its own, so
# these are resolved here and passed to run() explicitly. Values mirror the SDK
# defaults, keeping the FASTMCP_* names that earlier versions accepted.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
MIN_PORT = 1
MAX_PORT = 65535
SSE_PATH = "/sse"
MESSAGE_PATH = "/messages/"
STREAMABLE_HTTP_PATH = "/mcp"


def resolve_log_level() -> LogLevel:
    """
    Resolve the server log level from FASTMCP_LOG_LEVEL.

    Returns:
        LogLevel: The configured level, defaulting to INFO.

    Raises:
        ValueError: If the value is not a recognised level.
    """
    level = os.getenv("FASTMCP_LOG_LEVEL", "INFO").upper()
    if level not in LOG_LEVELS:
        allowed = ", ".join(LOG_LEVELS)
        raise ValueError(f"Unsupported FASTMCP_LOG_LEVEL value. Use one of: {allowed}.")
    return cast(LogLevel, level)


def _resolve_bind_address() -> tuple[str, int]:
    """
    Resolve the host and port for the network transports.

    Returns:
        tuple[str, int]: The host and port to bind to.

    Raises:
        ValueError: If FASTMCP_PORT is not an integer in the range 1-65535.
    """
    host = os.getenv("FASTMCP_HOST", DEFAULT_HOST)
    port_env = os.getenv("FASTMCP_PORT")

    if port_env is None:
        return host, DEFAULT_PORT

    try:
        port = int(port_env)
    except ValueError as exc:
        raise ValueError(f"FASTMCP_PORT must be an integer, got {port_env!r}.") from exc

    # int() only validates syntax; out-of-range values would otherwise surface as
    # an opaque socket error at bind time. Port 0 is excluded because the OS would
    # pick an arbitrary port, contradicting the URL logged below.
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"FASTMCP_PORT must be between {MIN_PORT} and {MAX_PORT}, got {port}.")

    return host, port


def setup_transport() -> TransportAliases:
    """
    Setup and validate the MCP transport configuration.

    Reads MCP_TRANSPORT environment variable and validates it against
    supported transport types.

    Returns:
        TransportAliases: The selected transport type.

    Raises:
        ValueError: If the transport type is not supported.
    """
    transport_env = os.getenv("MCP_TRANSPORT", TransportAliases.STDIO.value).lower()
    try:
        transport_alias = TransportAliases(transport_env)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in TransportAliases)
        raise ValueError(f"Unsupported MCP_TRANSPORT value. Use one of: {allowed}.") from exc

    # Map HTTP to STREAMABLE_HTTP
    selected_transport = (
        TransportAliases.STREAMABLE_HTTP
        if transport_alias == TransportAliases.HTTP
        else transport_alias
    )

    return selected_transport


def start_server(mcp_instance: MCPServer, transport: TransportAliases) -> None:
    """
    Start the MCP server with the specified transport.

    Args:
        mcp_instance (MCPServer): The MCPServer instance to start.
        transport (TransportAliases): The transport type to use.

    Raises:
        ValueError: If FASTMCP_PORT is not an integer, or if the removed
            MCP_SSE_MOUNT_PATH variable is set.
    """
    if transport == TransportAliases.STDIO:
        logger.info("Starting MCP server with stdio transport.")
        mcp_instance.run()
        return

    if os.getenv("MCP_SSE_MOUNT_PATH"):
        raise ValueError(
            "MCP_SSE_MOUNT_PATH is no longer supported: MCP SDK v2 removed the "
            "mount_path option. Mount the app behind a reverse proxy, or serve it "
            "under a sub-path with your own ASGI app."
        )

    host, port = _resolve_bind_address()

    if transport == TransportAliases.SSE:
        logger.info(
            "Starting MCP server with SSE transport at http://%s:%s%s (messages: %s).",
            host,
            port,
            SSE_PATH,
            MESSAGE_PATH,
        )
        mcp_instance.run(
            transport="sse",
            host=host,
            port=port,
            sse_path=SSE_PATH,
            message_path=MESSAGE_PATH,
        )
    else:  # STREAMABLE_HTTP
        logger.info(
            "Starting MCP server with Streamable HTTP transport at http://%s:%s%s.",
            host,
            port,
            STREAMABLE_HTTP_PATH,
        )
        mcp_instance.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=STREAMABLE_HTTP_PATH,
        )
