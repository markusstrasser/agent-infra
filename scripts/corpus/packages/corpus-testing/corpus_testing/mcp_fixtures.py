"""FastMCP-native test fixtures.

Optional — requires `corpus-testing[mcp]` extra (fastmcp dependency).
Pattern: spawn `Client(server)` async fixture so the MCP under test runs in
the same process. Sub-ms tool roundtrips, no transport setup.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

import pytest


@pytest.fixture
async def mcp_client(request) -> AsyncIterator[Any]:
    """Async FastMCP Client bound to a server provided via request.param.

    Usage:
        @pytest.fixture
        def server():
            from my_mcp.server import create_mcp
            return create_mcp()

        @pytest.mark.parametrize("mcp_client", [...], indirect=True)
        async def test_tool(mcp_client):
            r = await mcp_client.call_tool("my_tool", {...})
    """
    from fastmcp import Client  # local import keeps fastmcp optional

    server = request.param if hasattr(request, "param") else request.getfixturevalue("server")
    async with Client(server) as client:
        yield client
