import logging
import sys

import httpx
from starlette.responses import JSONResponse

from config import settings
from server import mcp

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Import tools to register them as a side-effect
import tools  # noqa: F401


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    """Health check returning MCP server status and Node-RED connectivity."""
    nodered_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.node_red_url}/api/status")
            if resp.status_code == 200:
                nodered_status = "connected"
            else:
                nodered_status = f"unhealthy ({resp.status_code})"
    except Exception as exc:
        nodered_status = f"unavailable ({type(exc).__name__})"
        logger.warning("Health check: Node-RED unreachable: %s", exc)

    return JSONResponse(
        {
            "status": "healthy" if nodered_status == "connected" else "degraded",
            "nodered": nodered_status,
        }
    )


app = mcp.streamable_http_app()

logger.info("SmartHome MCP Server starting on %s:%s", settings.mcp_host, settings.mcp_port)
logger.info("8 tools registered")
