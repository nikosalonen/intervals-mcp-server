"""
Shared MCP instance module.

This module provides a shared FastMCP instance that can be imported by both
the server module and tool modules without creating cyclic imports.
"""

from typing import Any

# Typed as Any to avoid union-attr errors in tool modules that call mcp.tool()
# before server.py initializes it. Actual runtime type is FastMCP once initialized.
mcp: Any = None  # pylint: disable=invalid-name  # This is a module-level variable, not a constant
