from __future__ import annotations

import logging
from datetime import datetime

from .state import SmartHomeState
from .mcp_client import MCPClient
from .config import AgentSettings

logger = logging.getLogger(__name__)

settings = AgentSettings()

# Thresholds used by evaluating_node (not yet in AgentSettings)
GAS_PRECRITICAL_THRESHOLD = 800
TEMP_WARNING_THRESHOLD = 28.0
SOUND_WARNING_THRESHOLD = 85.0
SENSOR_STALE_SECONDS = 60

CRITICAL_GAS_THRESHOLD = settings.critical_gas_threshold
CRITICAL_TEMP_THRESHOLD = settings.critical_temp_threshold


async def monitoring_node(state: SmartHomeState) -> dict:
    """Read sensor data via MCP and update state."""
    result: dict = {}

    try:
        mcp_client = MCPClient(url=settings.mcp_server_url)
        sensor_data = await mcp_client.call_tool("get_sensor_state")

        result["temperature"] = float(sensor_data.get("temperature", 0.0))
        result["humidity"] = float(sensor_data.get("humidity", 0.0))
        result["gas_ppm"] = int(sensor_data.get("gas_ppm", 0))
        result["sound_db"] = float(sensor_data.get("sound_db", 0.0))
        result["sensor_ts"] = sensor_data.get("timestamp", datetime.now().isoformat())
        result["mcp_connected"] = True

        # Staleness check
        try:
            ts = datetime.fromisoformat(result["sensor_ts"])
            now = datetime.now()
            if (now - ts).total_seconds() > SENSOR_STALE_SECONDS:
                result["sensor_stale"] = True
            else:
                result["sensor_stale"] = False
        except (ValueError, TypeError):
            result["sensor_stale"] = True

    except Exception as exc:
        logger.warning("MCP call failed in monitoring_node: %s", exc)
        result["error_type"] = "mcp_unreachable"
        result["mcp_connected"] = False
        result["sensor_stale"] = True

    # Always increment cycle and timestamp
    result["cycle_count"] = state.get("cycle_count", 0) + 1
    result["last_evaluation_ts"] = datetime.now().isoformat()

    return result


async def critical_handler_node(state: SmartHomeState) -> dict:
    """Build deterministic action plan for critical thresholds. NO LLM CALL."""
    gas_ppm = state.get("gas_ppm", 0)
    temperature = state.get("temperature", 0.0)

    action_plan: list[dict] = []
    last_critical = ""
    reason = ""

    if gas_ppm > CRITICAL_GAS_THRESHOLD:
        action_plan = [
            {"tool": "activate_led_alerta", "args": {"estado": True}},
            {"tool": "send_notification", "args": {"mensaje": f"⚠️ CRÍTICO: Gas elevado — {gas_ppm} ppm"}},
            {"tool": "trigger_camera", "args": {"duracion": 5}},
        ]
        last_critical = "gas"
        reason = f"gas {gas_ppm} ppm > {CRITICAL_GAS_THRESHOLD}"
    elif temperature > CRITICAL_TEMP_THRESHOLD:
        action_plan = [
            {"tool": "activate_led_alerta", "args": {"estado": True}},
            {"tool": "send_notification", "args": {"mensaje": f"⚠️ ALERTA: Temperatura elevada — {temperature}°C"}},
        ]
        last_critical = "temp"
        reason = f"temperatura {temperature}°C > {CRITICAL_TEMP_THRESHOLD}°C"

    return {
        "critical_active": True,
        "last_critical": last_critical,
        "llm_decision": {
            "nivel": "critico",
            "razonamiento": f"Umbral crítico superado: {reason}",
            "acciones": action_plan,
            "confidence": 1.0,
        },
        "pending_actions": action_plan,
    }


async def evaluating_node(state: SmartHomeState) -> dict:
    """Evaluate sensor readings against thresholds."""
    gas_ppm = state.get("gas_ppm", 0)
    temperature = state.get("temperature", 0.0)
    sound_db = state.get("sound_db", 0.0)

    anomaly_detected = (
        gas_ppm > GAS_PRECRITICAL_THRESHOLD
        or temperature > TEMP_WARNING_THRESHOLD
        or sound_db > SOUND_WARNING_THRESHOLD
    )

    result: dict = {
        "anomaly_detected": anomaly_detected,
        "trend_rising": False,
    }

    if anomaly_detected:
        result["normal_readings"] = 0
    else:
        result["normal_readings"] = state.get("normal_readings", 0) + 1

    return result
