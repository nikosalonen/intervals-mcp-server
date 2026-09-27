"""
Tests for transport selection and server startup.

These cover the FASTMCP_* wiring that lives in this project rather than the SDK.

Contrary to appearances, this is not migration parity work. v1 declared an
`env_prefix` of "FASTMCP_" on its Settings model but `FastMCP.__init__` then
passed an explicit argument for every field, and init arguments outrank env
sources in pydantic-settings -- so the prefix was decorative and none of these
variables ever took effect. Verified against mcp==1.29.0, the version this
project migrated from:

    FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=9999 FASTMCP_LOG_LEVEL=DEBUG
      -> settings.host='127.0.0.1'  settings.port=8000  settings.log_level='INFO'

v2 drops the pretense and reads no environment at all, so `start_server` resolves
these itself -- which makes the README SSE/ChatGPT instructions work for the
first time. The tests below pin that behavior, not a restored status quo.
"""

import inspect
import logging
import os
import subprocess
import sys
import typing
from typing import Any

import pytest
from mcp.server.mcpserver import MCPServer

from intervals_mcp_server import server_setup as ss
from intervals_mcp_server.config import LOG_LEVELS, resolve_log_level
from intervals_mcp_server.server_setup import (
    setup_transport,
    start_server,
)
from intervals_mcp_server.utils.types import TransportAliases


class RecordingServer:
    """Stands in for MCPServer, capturing what run() was called with."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append({"args": args, "kwargs": kwargs})

    @property
    def last(self) -> dict[str, Any]:
        assert self.calls, "run() was never called"
        return self.calls[-1]


@pytest.fixture(autouse=True)
def _clear_transport_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ambient environment from leaking into assertions."""
    for var in (
        "MCP_TRANSPORT",
        "FASTMCP_HOST",
        "FASTMCP_PORT",
        "FASTMCP_LOG_LEVEL",
        "MCP_SSE_MOUNT_PATH",
    ):
        monkeypatch.delenv(var, raising=False)


# --- resolve_log_level -------------------------------------------------


def test_log_level_defaults_to_info() -> None:
    assert resolve_log_level() == "INFO"


def test_log_level_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FASTMCP_LOG_LEVEL", "debug")
    assert resolve_log_level() == "DEBUG"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("WARN", "WARNING"), ("warn", "WARNING"), ("FATAL", "CRITICAL")],
)
def test_common_level_aliases_are_accepted(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: str
) -> None:
    """Python's own logging module accepts WARN and FATAL, so operators will too."""
    monkeypatch.setenv("FASTMCP_LOG_LEVEL", raw)
    assert resolve_log_level() == expected


@pytest.mark.parametrize("raw", ["  debug  ", "debug\n"])
def test_surrounding_whitespace_is_stripped(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    """A trailing newline is what a .env file or `export` typo actually produces."""
    monkeypatch.setenv("FASTMCP_LOG_LEVEL", raw)
    assert resolve_log_level() == "DEBUG"


@pytest.mark.parametrize("raw", ["chatty", "", "   "])
def test_unknown_log_level_falls_back_to_info_without_raising(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, raw: str
) -> None:
    """
    resolve_log_level runs at import time (mcp_instance builds MCPServer at module
    level), so raising would make a log-verbosity typo break every import path --
    including pytest collection. Degrade to INFO and say so instead.
    """
    monkeypatch.setenv("FASTMCP_LOG_LEVEL", raw)

    with caplog.at_level(logging.WARNING, logger="intervals_icu_mcp_server"):
        assert resolve_log_level() == "INFO"

    assert "FASTMCP_LOG_LEVEL" in caplog.text
    assert repr(raw) in caplog.text, "the rejected value must appear in the warning"


def test_a_bad_log_level_does_not_break_importing_the_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guards the CLAUDE.md rule that config is validated without breaking imports."""
    env = {
        **os.environ,
        "FASTMCP_LOG_LEVEL": "chatty",
        "API_KEY": "x",
        "ATHLETE_ID": "i123456",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import intervals_mcp_server.tools.activities"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


# --- setup_transport ---------------------------------------------------


def test_defaults_to_stdio_when_unset() -> None:
    assert setup_transport() == TransportAliases.STDIO


def test_http_is_an_alias_for_streamable_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    assert setup_transport() == TransportAliases.STREAMABLE_HTTP


def test_transport_value_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "SSE")
    assert setup_transport() == TransportAliases.SSE


def test_unsupported_transport_names_the_allowed_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MCP_TRANSPORT", "carrier-pigeon")
    with pytest.raises(ValueError, match="Unsupported MCP_TRANSPORT"):
        setup_transport()


# --- start_server: stdio -----------------------------------------------


def test_stdio_runs_with_no_transport_options_at_all() -> None:
    """
    Asserted as an exact call rather than per-key: `kwargs.get("host") is None`
    also holds for run(transport="sse"), which would break stdio framing.
    """
    server = RecordingServer()
    start_server(server, TransportAliases.STDIO)  # type: ignore[arg-type]

    assert server.last == {"args": (), "kwargs": {}}


# --- start_server: network transports ----------------------------------


@pytest.mark.parametrize(
    ("transport", "expected"),
    [
        (TransportAliases.SSE, "sse"),
        (TransportAliases.STREAMABLE_HTTP, "streamable-http"),
    ],
)
def test_network_transport_forwards_host_and_port_from_env(
    monkeypatch: pytest.MonkeyPatch, transport: TransportAliases, expected: str
) -> None:
    """The SDK reads no environment, so these only work if we forward them."""
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    monkeypatch.setenv("FASTMCP_PORT", "8765")

    server = RecordingServer()
    start_server(server, transport)  # type: ignore[arg-type]

    kwargs = server.last["kwargs"]
    assert kwargs["transport"] == expected
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8765


@pytest.mark.parametrize(
    "transport", [TransportAliases.SSE, TransportAliases.STREAMABLE_HTTP]
)
def test_network_transport_falls_back_to_loopback_defaults(
    transport: TransportAliases,
) -> None:
    server = RecordingServer()
    start_server(server, transport)  # type: ignore[arg-type]

    kwargs = server.last["kwargs"]
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8000


def test_non_numeric_port_is_rejected_with_a_clear_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FASTMCP_PORT", "not-a-port")
    server = RecordingServer()

    with pytest.raises(ValueError, match="FASTMCP_PORT"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]


@pytest.mark.parametrize("port", ["-1", "0", "65536", "99999"])
def test_port_outside_the_valid_range_is_rejected(
    monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    """
    -1/65536/99999 would otherwise surface as an OverflowError from deep in the
    socket layer. 0 is different: it would bind *successfully* on an OS-chosen
    port, contradicting the URL start_server announces. Both are refused up front.
    """
    monkeypatch.setenv("FASTMCP_PORT", port)
    server = RecordingServer()

    with pytest.raises(ValueError, match="FASTMCP_PORT"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert not server.calls, "server must not start with an out-of-range port"


@pytest.mark.parametrize("port", ["1", "8765", "65535"])
def test_ports_at_the_edges_of_the_valid_range_are_accepted(
    monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    monkeypatch.setenv("FASTMCP_PORT", port)
    server = RecordingServer()

    start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert server.last["kwargs"]["port"] == int(port)


def test_host_is_honoured_when_only_the_host_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """The standard container config: bind every interface, leave the port default."""
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    server = RecordingServer()

    start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert server.last["kwargs"]["host"] == "0.0.0.0"
    assert server.last["kwargs"]["port"] == 8000


@pytest.mark.parametrize("raw", ["", "   "])
def test_blank_host_falls_back_to_loopback_rather_than_all_interfaces(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    """
    `FASTMCP_HOST=${HOST}` with HOST unset exports an empty string, so getenv's
    default never fires. bind("") means 0.0.0.0, which would also drop the SDK's
    auto-enabled DNS-rebinding protection on an unauthenticated server.
    """
    monkeypatch.setenv("FASTMCP_HOST", raw)
    server = RecordingServer()

    start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert server.last["kwargs"]["host"] == "127.0.0.1"


def test_surrounding_whitespace_is_stripped_from_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otherwise this dies at bind time as an opaque gaierror."""
    monkeypatch.setenv("FASTMCP_HOST", "  0.0.0.0  ")
    server = RecordingServer()

    start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert server.last["kwargs"]["host"] == "0.0.0.0"


def test_binding_beyond_loopback_warns_that_protection_is_not_auto_enabled(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """
    The SDK auto-enables DNS-rebinding protection only for loopback hosts
    (`host in ("127.0.0.1", "localhost", "::1")`). This server ships no auth,
    so a wider bind must not be silent.
    """
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    server = RecordingServer()

    with caplog.at_level(logging.WARNING, logger="intervals_icu_mcp_server"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert "0.0.0.0" in caplog.text
    assert "rebinding" in caplog.text.lower()


def test_loopback_bind_stays_quiet(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("FASTMCP_HOST", "127.0.0.1")
    server = RecordingServer()

    with caplog.at_level(logging.WARNING, logger="intervals_icu_mcp_server"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert "rebinding" not in caplog.text.lower()


@pytest.mark.parametrize("raw", ["80_80", "８０８０", "+80"])
def test_ports_that_only_int_would_accept_are_rejected(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    """int() takes underscores and non-ASCII digits, silently landing on a different port."""
    monkeypatch.setenv("FASTMCP_PORT", raw)
    server = RecordingServer()

    with pytest.raises(ValueError, match="FASTMCP_PORT"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert not server.calls


# --- start_server: the bind banner ------------------------------------


@pytest.mark.parametrize(
    ("transport", "expected_url"),
    [
        (TransportAliases.SSE, "http://127.0.0.1:8000/sse"),
        (TransportAliases.STREAMABLE_HTTP, "http://127.0.0.1:8000/mcp"),
    ],
)
def test_bind_url_is_announced_even_when_logging_is_silenced(
    capsys: pytest.CaptureFixture[str],
    transport: TransportAliases,
    expected_url: str,
) -> None:
    """
    README tells the ChatGPT connector user to copy this URL out of the startup
    output, so FASTMCP_LOG_LEVEL=ERROR must not be able to suppress it.
    """
    logger = logging.getLogger("intervals_icu_mcp_server")
    original = logger.level
    logger.setLevel(logging.CRITICAL)
    try:
        start_server(RecordingServer(), transport)  # type: ignore[arg-type]
    finally:
        logger.setLevel(original)

    assert expected_url in capsys.readouterr().err


# --- start_server: MCP_SSE_MOUNT_PATH ---------------------------------


def test_sse_mount_path_fails_loudly_rather_than_being_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    MCP SDK v2 removed run(mount_path=...). Honouring the variable would need
    manual lifespan wiring, so refuse it outright instead of silently serving
    from the root and leaving the operator to discover the change in traffic.
    """
    monkeypatch.setenv("MCP_SSE_MOUNT_PATH", "/intervals")
    server = RecordingServer()

    with pytest.raises(ValueError, match="MCP_SSE_MOUNT_PATH"):
        start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert not server.calls, "server must not start with an unsupported mount path"


@pytest.mark.parametrize("raw", ["", "/"])
def test_mount_paths_that_never_did_anything_are_treated_as_unset(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    """`/` was v1's own default and a provable no-op, so refusing to boot on it is wrong."""
    monkeypatch.setenv("MCP_SSE_MOUNT_PATH", raw)
    server = RecordingServer()

    start_server(server, TransportAliases.SSE)  # type: ignore[arg-type]

    assert server.last["kwargs"]["transport"] == "sse"


def test_mount_path_only_warns_on_transports_that_never_read_it(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """
    v1 read mount_path only in the SSE branch, so a stale .env line must not
    newly refuse to start a streamable-http server that worked before.
    """
    monkeypatch.setenv("MCP_SSE_MOUNT_PATH", "/intervals")
    server = RecordingServer()

    with caplog.at_level(logging.WARNING, logger="intervals_icu_mcp_server"):
        start_server(server, TransportAliases.STREAMABLE_HTTP)  # type: ignore[arg-type]

    assert server.last["kwargs"]["transport"] == "streamable-http"
    assert "MCP_SSE_MOUNT_PATH" in caplog.text


def test_mount_path_is_ignored_for_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SSE_MOUNT_PATH", "/intervals")
    server = RecordingServer()

    start_server(server, TransportAliases.STDIO)  # type: ignore[arg-type]

    assert server.last == {"args": (), "kwargs": {}}


# --- contracts against the installed SDK ------------------------------


@pytest.mark.parametrize(
    ("transport", "method"),
    [
        (TransportAliases.SSE, MCPServer.run_sse_async),
        (TransportAliases.STREAMABLE_HTTP, MCPServer.run_streamable_http_async),
    ],
)
def test_run_kwargs_bind_to_the_real_sdk_signature(
    transport: TransportAliases, method: Any
) -> None:
    """
    run() forwards **kwargs: Any straight through, so mypy cannot see an SDK
    rename and RecordingServer would happily swallow one. Bind for real.
    """
    server = RecordingServer()
    start_server(server, transport)  # type: ignore[arg-type]

    kwargs = dict(server.last["kwargs"])
    del kwargs["transport"]
    inspect.signature(method).bind(object(), **kwargs)


def test_path_constants_still_match_the_sdk_defaults() -> None:
    """
    These are pinned deliberately, not derived -- README publishes them. The test
    exists so an SDK default moving under us is a visible decision, not a drift.
    """
    sse = inspect.signature(MCPServer.run_sse_async).parameters
    http = inspect.signature(MCPServer.run_streamable_http_async).parameters

    assert sse["sse_path"].default == ss.SSE_PATH
    assert sse["message_path"].default == ss.MESSAGE_PATH
    assert http["streamable_http_path"].default == ss.STREAMABLE_HTTP_PATH
    assert sse["host"].default == ss.DEFAULT_HOST
    assert sse["port"].default == ss.DEFAULT_PORT


def test_log_levels_match_the_sdk_literal() -> None:
    hints = typing.get_type_hints(MCPServer.__init__)
    assert set(typing.get_args(hints["log_level"])) == set(LOG_LEVELS)


def test_log_level_reaches_the_mcpserver_instance() -> None:
    """
    mcp_instance builds MCPServer at import time, so this runs in a subprocess:
    reloading the module would create a second instance while tools/ still hold
    the first, corrupting tool registration for the rest of the session.
    """
    env = {
        **os.environ,
        "FASTMCP_LOG_LEVEL": "warning",
        "API_KEY": "x",
        "ATHLETE_ID": "i123456",
    }
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from intervals_mcp_server.mcp_instance import mcp; print(mcp.settings.log_level)",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip() == "WARNING"


def test_server_reports_its_package_version_to_clients() -> None:
    """An empty serverInfo.version shows up as blank in clients that surface it."""
    env = {**os.environ, "API_KEY": "x", "ATHLETE_ID": "i123456"}
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from intervals_mcp_server.mcp_instance import mcp;"
            "print(mcp._lowlevel_server.create_initialization_options().server_version)",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip(), "serverInfo.version must not be empty"
