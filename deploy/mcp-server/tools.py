import json
import logging
from typing import Optional

import httpx
from mcp import McpError
from mcp.types import ErrorData, TextContent

from config import settings
from nodered_client import NodeRedClient

logger = logging.getLogger(__name__)

_nodered_client = NodeRedClient(settings.node_red_url)
_twin_client: Optional[NodeRedClient] = None
if settings.digital_twin_url:
    _twin_client = NodeRedClient(settings.digital_twin_url)


def _info_client() -> NodeRedClient:
    return _twin_client or _nodered_client


def _action_client() -> NodeRedClient:
    return _nodered_client


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, httpx.TimeoutException):
        raise McpError(ErrorData(code=-32603, message="Node-RED request timed out"))
    if isinstance(exc, httpx.ConnectError):
        raise McpError(ErrorData(code=-32603, message="Node-RED unavailable"))
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        try:
            body = exc.response.json()
        except Exception:
            body = {}
        msg = body.get("error", f"Node-RED returned {status}")
        if status == 503:
            raise McpError(ErrorData(code=-32603, message=f"Service unavailable: {msg}"))
        if status in (400, 422):
            raise McpError(ErrorData(code=-32602, message=f"Invalid params: {msg}"))
        raise McpError(ErrorData(code=-32603, message=f"Node-RED error {status}: {msg}"))
    raise McpError(ErrorData(code=-32603, message=f"Unexpected error: {str(exc)}"))


from server import mcp


@mcp.tool()
async def get_sensor_state() -> str:
    """Get current sensor readings (temperature, humidity, gas, sound)."""
    try:
        data = await _info_client().get_sensor_state()
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def get_system_status() -> str:
    """Get the logical system status (LED and alert states)."""
    try:
        data = await _action_client().get_system_status()
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def query_history(
    from_time: Optional[str] = None,
    to_time: Optional[str] = None,
    limit: Optional[int] = None,
) -> str:
    """Query historical sensor data from CSV."""
    try:
        data = await _info_client().query_history(from_time, to_time, limit)
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def activate_led_alerta(estado: bool) -> str:
    """Activate or deactivate the alert LED."""
    try:
        data = await _action_client().activate_led_alerta(estado)
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def activate_led_puerta(accion: str) -> str:
    """Activate or deactivate the door LED."""
    try:
        data = await _action_client().activate_led_puerta(accion)
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def send_notification(mensaje: str) -> str:
    """Send a notification message via Telegram."""
    try:
        data = await _action_client().send_notification(mensaje)
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def silence_alerts() -> str:
    """Silence all active alerts."""
    try:
        data = await _action_client().silence_alerts()
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)


@mcp.tool()
async def trigger_camera(duracion: int) -> str:
    """Trigger the camera to capture for a given duration."""
    try:
        data = await _action_client().trigger_camera(duracion)
        return json.dumps(data)
    except Exception as exc:
        _handle_error(exc)
