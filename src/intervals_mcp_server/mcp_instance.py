"""
Shared MCP instance module.

This module provides a shared MCPServer instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer  # pylint: disable=import-error

from intervals_mcp_server.api.client import setup_api_client
from intervals_mcp_server.server_setup import resolve_log_level

mcp: MCPServer = MCPServer(  # pylint: disable=invalid-name
    "intervals-icu",
    lifespan=setup_api_client,
    log_level=resolve_log_level(),
)
