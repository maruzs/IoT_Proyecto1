from __future__ import annotations

import json
import logging

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Cliente MCP usando el SDK oficial (mcp>=1.0.0).

    El MCP Server (deploy/mcp-server/) usa FastMCP con streamable_http_app().
    Las 8 tools devuelven str (JSON), por lo que parseamos después de call_tool.
    """

    def __init__(self, url: str = "https://mcp-server:8002/mcp"):
        self.url = url

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Call an MCP tool and return parsed JSON result."""
        # Docker internal TLS with self-signed cert — disable verification
        async with streamablehttp_client(
            self.url,
            httpx_client_factory=lambda: httpx.AsyncClient(verify=False),
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments or {})
                # MCP Server tools return str (JSON-serialized)
                return json.loads(result.content[0].text)

    async def list_tools(self) -> list[dict]:
        """Discover available tools from the MCP Server."""
        async with streamablehttp_client(
            self.url,
            httpx_client_factory=lambda: httpx.AsyncClient(verify=False),
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {"name": t.name, "description": t.description}
                    for t in result.tools
                ]
