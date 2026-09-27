"""
Unit tests for the make_intervals_request function in intervals_mcp_server.server.

These tests focus on error handling, particularly the scenario where the API returns invalid JSON.
Mock classes are used to simulate httpx responses and client behavior.
"""

import asyncio
import logging
import os
import pathlib
import sys
from json import JSONDecodeError

import httpx
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server import server  # pylint: disable=wrong-import-position
from intervals_mcp_server.api import client as api_client  # pylint: disable=wrong-import-position
from intervals_mcp_server.config import Config  # pylint: disable=wrong-import-position


class MockBadJSONResponse:
    """
    Simulates an httpx response object that returns invalid JSON content.
    Used to test error handling for JSONDecodeError in make_intervals_request.
    """

    def __init__(self):
        self.content = b"bad"
        self.status_code = 200

    def raise_for_status(self):
        """Mock raise_for_status that does nothing."""
        return None

    def json(self):
        """Raise JSONDecodeError to simulate invalid JSON."""
        raise JSONDecodeError("Expecting value", "bad", 0)


class MockAsyncClient:
    """
    Simulates an httpx.AsyncClient for use in monkeypatching.
    Always returns a MockBadJSONResponse from get().
    """

    def __init__(self, *_args, **_kwargs):
        # Accept any arguments to match httpx.AsyncClient's interface
        self.is_closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get(self, _url, **_kwargs):
        """Mock get method that returns MockBadJSONResponse."""
        return MockBadJSONResponse()

    async def request(self, *_args, **_kwargs):
        """Mock request method that returns MockBadJSONResponse."""
        return MockBadJSONResponse()

    async def aclose(self):
        """Simulate closing the AsyncClient."""
        self.is_closed = True


def test_make_intervals_request_bad_json(monkeypatch, caplog):
    """
    Test that make_intervals_request returns an error dict when the response contains invalid JSON.
    Ensures proper logging and error message content.
    """
    monkeypatch.setenv("API_KEY", "test")
    monkeypatch.setenv("ATHLETE_ID", "i1")
    # Reset the singleton so config picks up the monkeypatched env vars
    monkeypatch.setattr("intervals_mcp_server.config._config_instance", None)
    monkeypatch.setattr(server, "httpx_client", MockAsyncClient())
    monkeypatch.setattr(
        api_client,
        "get_config",
        lambda: Config(
            api_key="test",
            athlete_id="i1",
            intervals_api_base_url="https://intervals.icu/api/v1",
            user_agent="test-agent",
        ),
    )

    # Ensure the config singleton has an API key, regardless of test execution order
    from intervals_mcp_server.config import get_config
    monkeypatch.setattr(get_config(), "api_key", "test")

    with caplog.at_level(logging.ERROR):
        result = asyncio.run(server.make_intervals_request("/bad"))

    assert result["error"] is True
    assert "Invalid JSON in response" in result["message"]


@pytest.fixture
def use_mock_transport(monkeypatch):
    """Route make_intervals_request through an httpx.MockTransport returning a fixed response.

    Yields a function taking (status_code, body). The client is closed after the test.
    """
    clients: list[httpx.AsyncClient] = []

    def _use(status_code: int, body: bytes) -> None:
        transport = httpx.MockTransport(lambda _request: httpx.Response(status_code, content=body))
        client = httpx.AsyncClient(transport=transport)
        clients.append(client)
        monkeypatch.setattr(server, "httpx_client", client)
        monkeypatch.setattr(
            api_client,
            "get_config",
            lambda: Config(
                api_key="test",
                athlete_id="i1",
                intervals_api_base_url="https://intervals.icu/api/v1",
                user_agent="test-agent",
            ),
        )

    yield _use
    for client in clients:
        asyncio.run(client.aclose())


@pytest.mark.parametrize(
    ("status_code", "body", "expected"),
    [
        (401, b"Unauthorized", "401 Unauthorized: Please check your API key"),
        (502, b"<html>Bad Gateway</html>", "502 Bad Gateway: Temporary upstream error; retry shortly."),
        (
            502,
            b"upstream connect error",
            "502 Bad Gateway: Temporary upstream error; retry shortly. Details: upstream connect error",
        ),
        (
            422,
            b'{"error": "start_date_local is required"}',
            'Details: {"error": "start_date_local is required"}',
        ),
        (400, b"start_date_local is required", "400 Bad Request: start_date_local is required"),
        (409, b"", "409 Conflict: Intervals.icu returned no readable error details."),
        (520, b"<html>Unknown</html>", "520: Intervals.icu returned no readable error details."),
    ],
)
def test_make_intervals_request_non_json_error_body_keeps_status(
    use_mock_transport, status_code, body, expected
):
    """A non-JSON error body reports the HTTP status, not an 'Invalid JSON' error."""
    use_mock_transport(status_code, body)

    result = asyncio.run(server.make_intervals_request("/athlete/i1"))

    assert isinstance(result, dict)
    assert result["status_code"] == status_code
    assert expected in result["message"]
    assert "<html>" not in result["message"]


def test_make_intervals_request_mapped_error_without_readable_body_has_no_details(
    use_mock_transport,
):
    """A mapped status with an HTML body returns only the fixed message."""
    use_mock_transport(504, b"<html>Gateway Timeout</html>")

    result = asyncio.run(server.make_intervals_request("/athlete/i1"))

    assert isinstance(result, dict)
    assert result["message"] == "504 Gateway Timeout: Temporary upstream timeout; retry shortly."


def test_make_intervals_request_truncates_long_error_body(use_mock_transport):
    """A long plain-text error body is cut short instead of flooding the tool output."""
    use_mock_transport(400, b"x" * 5000)

    result = asyncio.run(server.make_intervals_request("/athlete/i1"))

    assert isinstance(result, dict)
    assert result["message"].startswith("400 Bad Request: xxx")
    assert len(result["message"]) < 600
