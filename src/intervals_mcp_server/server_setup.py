"""
Server setup and initialization for Intervals.icu MCP Server.

This module handles transport configuration and server startup logic.
"""

import os
import logging
import sys

from mcp.server.mcpserver import MCPServer  # pylint: disable=import-error

from intervals_mcp_server.utils.types import TransportAliases

logger = logging.getLogger("intervals_icu_mcp_server")

# SDK v2 reads no environment of its own, so the functions below resolve FASTMCP_*
# here and start_server passes the results to run() explicitly. The names are kept
# from v1, which declared an env_prefix of "FASTMCP_" but then shadowed every field
# with an explicit constructor argument -- so these variables never actually took
# effect before, and README's SSE instructions have been silently ignored until now.
#
# The paths are pinned rather than left to the SDK: README publishes /sse, /messages/
# and /mcp as this server's endpoints, so they must not move if an SDK default does.
# test_path_constants_still_match_the_sdk_defaults keeps the two in view of each other.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
SSE_PATH = "/sse"
MESSAGE_PATH = "/messages/"
STREAMABLE_HTTP_PATH = "/mcp"

# IANA range. 0 is excluded deliberately -- see _resolve_bind_address.
MIN_PORT = 1
MAX_PORT = 65535

# The hosts for which the SDK auto-enables DNS-rebinding protection; mirrors the
# check in MCPServer.sse_app / streamable_http_app.
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _announce(message: str) -> None:
    """
    Write an operational line to stderr, bypassing the log level.

    The bind banner tells the operator which URL to connect to, and README's
    ChatGPT connector instructions tell them to copy it from this output. A
    FASTMCP_LOG_LEVEL of ERROR must therefore not be able to suppress it.
    stderr keeps it clear of the stdio transport's protocol stream on stdout.
    """
    print(message, file=sys.stderr, flush=True)


def _resolve_host() -> str:
    """
    Resolve the bind host from FASTMCP_HOST.

    An exported-but-empty value falls back to the loopback default instead of
    being passed through: bind("") means every interface, which would also drop
    the SDK's auto-enabled DNS-rebinding protection on a server that ships no
    authentication. Warns when the resulting bind is wider than loopback.

    Returns:
        str: The host to bind to.
    """
    host = os.getenv("FASTMCP_HOST", "").strip() or DEFAULT_HOST

    if host not in LOOPBACK_HOSTS:
        logger.warning(
            "Binding to %s, which is reachable beyond localhost. The MCP SDK only "
            "auto-enables DNS-rebinding protection for %s, and this server ships no "
            "authentication -- put it behind a proxy that terminates TLS and authenticates.",
            host,
            ", ".join(LOOPBACK_HOSTS),
        )

    return host


def _resolve_port() -> int:
    """
    Resolve the bind port from FASTMCP_PORT.

    Returns:
        int: The port to bind to.

    Raises:
        ValueError: If the value is not a plain decimal integer in the range 1-65535.
    """
    port_env = os.getenv("FASTMCP_PORT")
    if port_env is None:
        return DEFAULT_PORT

    candidate = port_env.strip()
    # int() is looser than this contract: it accepts "80_80" (-> 8080), "+80" and
    # non-ASCII digits, each of which would silently bind a port the operator did
    # not write. Require plain ASCII decimal digits instead.
    if not (candidate.isascii() and candidate.isdigit()):
        raise ValueError(f"FASTMCP_PORT must be a decimal integer, got {port_env!r}.")

    port = int(candidate)

    # Range is checked separately because out-of-range values would otherwise
    # surface as an opaque OverflowError from the socket layer at bind time. Port 0
    # is excluded because the OS would pick an arbitrary port, contradicting the
    # URL that start_server announces.
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"FASTMCP_PORT must be between {MIN_PORT} and {MAX_PORT}, got {port}.")

    return port


def _check_mount_path(transport: TransportAliases) -> None:
    """
    Reject MCP_SSE_MOUNT_PATH, which SDK v2 can no longer honour.

    This is the project's own variable, not the SDK's; what v2 removed is
    `run(mount_path=...)`. Honouring it would mean hand-wiring the lifespan of a
    mounted sub-app, so it fails loudly rather than silently serving from the root.

    Empty and "/" are treated as unset: "/" was v1's own default and a provable
    no-op. Only SSE raises, because v1 read mount_path only in its SSE branch --
    refusing to boot a streamable-http server that worked before would be a
    regression, so that case warns instead.

    Args:
        transport (TransportAliases): The transport about to be started.

    Raises:
        ValueError: If a real sub-path is set and the transport is SSE.
    """
    mount_path = os.getenv("MCP_SSE_MOUNT_PATH", "").strip().strip("/")
    if not mount_path:
        return

    detail = (
        "MCP_SSE_MOUNT_PATH is no longer supported: MCP SDK v2 removed the "
        "mount_path option. Mount the app behind a reverse proxy, or serve it "
        "under a sub-path with your own ASGI app."
    )

    if transport == TransportAliases.SSE:
        raise ValueError(detail)

    logger.warning("Ignoring MCP_SSE_MOUNT_PATH on the %s transport: %s", transport.value, detail)


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
    transport_env = os.getenv("MCP_TRANSPORT", TransportAliases.STDIO.value).strip().lower()
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
        ValueError: If FASTMCP_PORT is not a decimal integer in the range 1-65535,
            or if MCP_SSE_MOUNT_PATH names a sub-path and the transport is SSE.
    """
    if transport == TransportAliases.STDIO:
        logger.info("Starting MCP server with stdio transport.")
        mcp_instance.run()
        return

    _check_mount_path(transport)

    host = _resolve_host()
    port = _resolve_port()

    if transport == TransportAliases.SSE:
        _announce(
            f"Starting MCP server with SSE transport at "
            f"http://{host}:{port}{SSE_PATH} (messages: {MESSAGE_PATH})."
        )
        mcp_instance.run(
            transport="sse",
            host=host,
            port=port,
            sse_path=SSE_PATH,
            message_path=MESSAGE_PATH,
        )
    else:  # STREAMABLE_HTTP
        _announce(
            f"Starting MCP server with Streamable HTTP transport at "
            f"http://{host}:{port}{STREAMABLE_HTTP_PATH}."
        )
        mcp_instance.run(
            transport="streamable-http",
            host=host,
            port=port,
            streamable_http_path=STREAMABLE_HTTP_PATH,
        )
