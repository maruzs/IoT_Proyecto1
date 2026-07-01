import json
import logging
from typing import Any, Dict, Optional

import httpx
from mcp import McpError
from mcp.types import ErrorData, TextContent

from config import settings
from nodered_client import NodeRedClient
from twin_client import DigitalTwinClient

logger = logging.getLogger(__name__)

_nodered_client = NodeRedClient(settings.node_red_url)

# Digital Twin client — consumes GET /gemelo/estado (full consolidated state)
_twin_client: Optional[DigitalTwinClient] = None
if settings.digital_twin_url:
    _twin_client = DigitalTwinClient(settings.digital_twin_url)
    logger.info("Digital Twin client active: %s", settings.digital_twin_url)


def _info_client() -> DigitalTwinClient | NodeRedClient:
    """Return the info client — prefers Digital Twin if configured."""
    if _twin_client:
        return _twin_client
    return _nodered_client


def _action_client() -> NodeRedClient:
    """Return the action client — always Node-RED (gatekeeper)."""
    return _nodered_client


def _is_twin(client: DigitalTwinClient | NodeRedClient) -> bool:
    """Check if the given client is a DigitalTwinClient instance."""
    return isinstance(client, DigitalTwinClient)


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
    """Query historical sensor data — from DT (full state) or Node-RED (CSV)."""
    try:
        client = _info_client()
        if _is_twin(client):
            # Digital Twin returns full history array (no server-side filter)
            history = await client.get_history()
            if limit:
                history = history[:limit]
            return json.dumps(history)
        else:
            data = await client.query_history(from_time, to_time, limit)
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


@mcp.tool()
async def get_gemelo_estado() -> str:
    """Get the full Digital Twin state (sensors, history, alerts, predictions, LLM summary)."""
    try:
        client = _info_client()
        if _is_twin(client):
            data = await client.get_full_state()
        else:
            # Fallback: assemble from Node-RED endpoints
            sensors = await _nodered_client.get_sensor_state()
            status = await _nodered_client.get_system_status()
            data = {
                "estado_actual": sensors,
                "led_state": status.get("led_state", "UNKNOWN"),
                "alert_state": status.get("alert_state", "UNKNOWN"),
                "source": "nodered_fallback",
            }
        return json.dumps(data, indent=2, default=str)
    except Exception as exc:
        _handle_error(exc)
