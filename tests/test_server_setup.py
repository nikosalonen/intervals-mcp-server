"""
Tests for transport selection and server startup.

These cover the wiring that MCP SDK v2 no longer does implicitly: v1 read
FASTMCP_* environment variables via pydantic-settings, while v2 reads no
environment at all, so `start_server` must pass host/port explicitly.
"""

from typing import Any

import pytest

from intervals_mcp_server.server_setup import (
    resolve_log_level,
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


def test_unknown_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FASTMCP_LOG_LEVEL", "chatty")
    with pytest.raises(ValueError, match="FASTMCP_LOG_LEVEL"):
        resolve_log_level()


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


def test_stdio_runs_without_binding_a_socket() -> None:
    server = RecordingServer()
    start_server(server, TransportAliases.STDIO)  # type: ignore[arg-type]

    assert server.last["kwargs"].get("host") is None
    assert server.last["kwargs"].get("port") is None


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
    """v2 reads no environment itself, so we must forward these explicitly."""
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
