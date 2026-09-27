"""
Shared MCP instance module.

This module provides a shared MCPServer instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from mcp.server.mcpserver import MCPServer  # pylint: disable=import-error

from intervals_mcp_server.api.client import setup_api_client
from intervals_mcp_server.config import resolve_log_level

try:
    _VERSION = version("intervals-mcp-server")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    _VERSION = "0.0.0+unknown"

# v2 defaults `version` to "", which clients surface as a blank serverInfo.version.
# v1 happened to report the SDK's own version there, which was never meaningful.
mcp: MCPServer = MCPServer(  # pylint: disable=invalid-name
    "intervals-icu",
    version=_VERSION,
    lifespan=setup_api_client,
    log_level=resolve_log_level(),
)
