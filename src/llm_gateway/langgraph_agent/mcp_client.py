from __future__ import annotations

import json
import logging
import ssl

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
        # TLS interno de Docker con certificado autofirmado — desactivar verificación
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        self._ssl = ssl_context

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Call an MCP tool and return parsed JSON result."""
        async with streamablehttp_client(self.url, ssl_context=self._ssl) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments or {})
                # MCP Server tools return str (JSON-serialized)
                return json.loads(result.content[0].text)

    async def list_tools(self) -> list[dict]:
        """Discover available tools from the MCP Server."""
        async with streamablehttp_client(self.url, ssl_context=self._ssl) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {"name": t.name, "description": t.description}
                    for t in result.tools
                ]
