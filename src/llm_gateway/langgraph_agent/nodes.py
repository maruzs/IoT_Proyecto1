from __future__ import annotations

import asyncio
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

        result["temperature"] = float(sensor_data.get("temperatura", sensor_data.get("temperature", 0.0)))
        result["humidity"] = float(sensor_data.get("humedad", sensor_data.get("humidity", 0.0)))
        result["gas_ppm"] = int(sensor_data.get("gas", sensor_data.get("gas_ppm", 0)))
        result["sound_db"] = float(sensor_data.get("sonido", sensor_data.get("sound_db", 0.0)))
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


def _deterministic_fallback(state: SmartHomeState, error_type: str) -> dict:
    """Build a deterministic decision when LLM is unavailable or times out."""
    gas_ppm = state.get("gas_ppm", 0)
    temperature = state.get("temperature", 0.0)
    now = datetime.now().isoformat()

    if gas_ppm > 1020 or temperature > 30.0:
        nivel = "critico"
        actions = [
            {"tool": "activate_led_alerta", "args": {"estado": True}},
            {"tool": "send_notification", "args": {"mensaje": f"⚠️ CRÍTICO: Gas {gas_ppm} ppm / Temp {temperature}°C"}},
        ]
    elif gas_ppm > 800 or temperature > 28.0:
        nivel = "alto"
        actions = [
            {"tool": "send_notification", "args": {"mensaje": f"⚠️ ALTO: Gas {gas_ppm} ppm / Temp {temperature}°C"}},
        ]
    elif gas_ppm > 400:
        nivel = "medio"
        actions = [
            {"tool": "send_notification", "args": {"mensaje": f"⚠️ MEDIO: Gas {gas_ppm} ppm"}},
        ]
    else:
        nivel = "normal"
        actions = []

    llm_decision = {
        "nivel": nivel,
        "razonamiento": f"Fallback determinístico ({error_type}): umbral automático aplicado.",
        "acciones": actions,
        "confidence": 1.0,
        "timestamp": now,
    }

    pending_actions = actions if nivel != "normal" else []

    return {
        "llm_decision": llm_decision,
        "pending_actions": pending_actions,
        "needs_confirmation": False,
        "error_type": error_type,
    }


async def deciding_node(
    state: SmartHomeState,
    ollama_client=None,
    prompt_builder_fn=None,
) -> dict:
    """Query Ollama for a severity decision with 3s timeout and deterministic fallback."""
    # Lazy imports to avoid circular dependencies at module level
    if ollama_client is None:
        from ..ollama_client import OllamaClient
        from ..config import Settings

        _settings = Settings()
        ollama_client = OllamaClient(
            base_url=_settings.OLLAMA_URL,
            model=_settings.OLLAMA_MODEL,
            timeout=_settings.OLLAMA_TIMEOUT,
            max_retries=_settings.MAX_RETRIES,
        )
        client_created = True
    else:
        client_created = False

    if prompt_builder_fn is None:
        from ..prompt_builder import build_decision_prompt

        prompt_builder_fn = build_decision_prompt

    sensor_context = {
        "temperature": state.get("temperature", 0.0),
        "humidity": state.get("humidity", 0.0),
        "gas_ppm": state.get("gas_ppm", 0),
        "sound_db": state.get("sound_db", 0.0),
        "sensor_ts": state.get("sensor_ts", ""),
    }

    user_prompt, system_prompt = prompt_builder_fn(sensor_context)

    try:
        raw_response = await asyncio.wait_for(
            ollama_client.generate(user_prompt, system_prompt),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        logger.warning("LLM decision timed out after 3s, using deterministic fallback")
        if client_created:
            await ollama_client.close()
        return _deterministic_fallback(state, error_type="llm_timeout")
    except Exception as exc:
        logger.warning("LLM decision failed: %s, using deterministic fallback", exc)
        if client_created:
            await ollama_client.close()
        return _deterministic_fallback(state, error_type="llm_error")
    finally:
        if client_created:
            await ollama_client.close()

    from ..json_validator import extract_json

    parsed = extract_json(raw_response)
    if parsed is None:
        logger.warning("LLM returned invalid JSON, using deterministic fallback")
        return _deterministic_fallback(state, error_type="llm_error")

    # Normalize field names — spec expects nivel/razonamiento/acciones,
    # prompt_builder may return action/reason
    nivel = parsed.get("nivel") or parsed.get("action") or "normal"
    razonamiento = parsed.get("razonamiento") or parsed.get("reason") or ""
    confidence = float(parsed.get("confidence", 0.0))

    # Normalize acciones — may be a list of dicts, a list of strings, or a single string
    raw_acciones = parsed.get("acciones") or parsed.get("actions") or []
    if isinstance(raw_acciones, str):
        raw_acciones = [raw_acciones] if raw_acciones else []

    acciones: list[dict] = []
    for item in raw_acciones:
        if isinstance(item, dict):
            if "tool" in item:
                acciones.append(item)
            elif "nombre" in item:
                # Normalize phi3:mini nested format
                acciones.append({"tool": item["nombre"], "args": item.get("args", {})})
            else:
                acciones.append({"tool": str(item), "args": {}})
        elif isinstance(item, str) and item != "no_action":
            acciones.append({"tool": item, "args": {}})

    now = datetime.now().isoformat()
    llm_decision = {
        "nivel": nivel,
        "razonamiento": razonamiento,
        "acciones": acciones,
        "confidence": confidence,
        "timestamp": now,
    }

    # Build pending_actions from acciones (skip no_action)
    pending_actions = acciones.copy()

    # If the LLM explicitly says no_action, clear pending_actions
    if isinstance(parsed.get("action"), str) and parsed["action"] == "no_action":
        pending_actions = []
    if isinstance(parsed.get("nivel"), str) and parsed["nivel"] == "normal":
        pending_actions = []

    needs_confirmation = False
    if confidence < 0.8 and nivel != "normal" and pending_actions:
        needs_confirmation = True

    return {
        "llm_decision": llm_decision,
        "pending_actions": pending_actions,
        "needs_confirmation": needs_confirmation,
        "error_type": None,
    }


async def executing_node(state: SmartHomeState) -> dict:
    """Execute pending actions via MCP sequentially."""
    pending_actions = state.get("pending_actions", [])
    if not pending_actions:
        return {"mcp_results": [], "error_type": None, "retry_count": 0}

    mcp_client = MCPClient(url=settings.mcp_server_url)
    mcp_results: list[dict] = []
    retry_count = state.get("retry_count", 0)

    for action in pending_actions:
        tool_name = action.get("tool")
        args = action.get("args", {})
        if not tool_name:
            continue

        try:
            result = await mcp_client.call_tool(tool_name, args)
            mcp_results.append({
                "tool": tool_name,
                "success": True,
                "result": result,
                "error": None,
            })
        except Exception as exc:
            logger.warning("MCP tool call failed for %s: %s", tool_name, exc)
            mcp_results.append({
                "tool": tool_name,
                "success": False,
                "result": {},
                "error": str(exc),
            })
            return {
                "mcp_results": mcp_results,
                "error_type": "mcp_execution_fail",
                "retry_count": retry_count + 1,
            }

    return {
        "mcp_results": mcp_results,
        "error_type": None,
        "retry_count": 0,
    }


async def notifying_node(state: SmartHomeState) -> dict:
    """Prepare notification payload and reset state after a successful cycle."""
    existing = state.get("notification_payload")
    mcp_results = state.get("mcp_results", [])

    if existing:
        # Preserve payload set by upstream nodes (query, help, clarification, etc.)
        notification_payload = {
            **existing,
            "timestamp": existing.get("timestamp", datetime.now().isoformat()),
            "mcp_results": mcp_results,
        }
    else:
        llm_decision = state.get("llm_decision", {})
        notification_payload = {
            "nivel": llm_decision.get("nivel", "normal"),
            "razonamiento": llm_decision.get("razonamiento", ""),
            "acciones": llm_decision.get("acciones", []),
            "timestamp": llm_decision.get("timestamp", datetime.now().isoformat()),
            "mcp_results": mcp_results,
        }

    result: dict = {
        "notification_payload": notification_payload,
        "notification_ready": True,
    }

    if state.get("critical_active"):
        result["normal_readings"] = 0

    # Only reset degraded mode; preserve silenced so the scheduler respects it
    if state.get("mode") == "degraded":
        result["mode"] = "active"

    return result


async def error_handler_node(state: SmartHomeState) -> dict:
    """Log error, increment retry counter, and route to recovery or degraded."""
    error_type = state.get("error_type")
    retry_count = state.get("retry_count", 0) + 1
    max_retries = state.get("max_retries", 3)

    logger.warning(
        "Error handler triggered: %s (retry %d/%d)",
        error_type, retry_count, max_retries,
    )

    if retry_count <= max_retries:
        return {
            "error_type": None,
            "retry_count": retry_count,
        }

    return {
        "mode": "degraded",
        "degraded_since": datetime.now().isoformat(),
        "retry_count": 0,
    }


async def degraded_mode_node(state: SmartHomeState) -> dict:
    """Enter degraded mode: disable MCP, notify user, no LLM/MCP calls."""
    now = datetime.now().isoformat()
    notification_payload = {
        "nivel": "degraded",
        "razonamiento": (
            "El sistema entró en modo degradado debido a errores repetidos. "
            "No se pueden ejecutar acciones hasta que se recupere la conexión con MCP."
        ),
        "timestamp": now,
    }

    return {
        "mode": "degraded",
        "mcp_connected": False,
        "notification_payload": notification_payload,
        "notification_ready": True,
    }


async def receiving_input_node(state: SmartHomeState) -> dict:
    """Classify user input using the rule-first intent classifier."""
    user_input = state.get("user_input_raw")
    if not user_input:
        return {"classified_intent": None}

    from .intent_classifier import classify

    result = classify(user_input)
    return {
        "classified_intent": result.get("intent"),
        "intent_confidence": result.get("confidence", 0.0),
    }


async def command_router_node(state: SmartHomeState) -> dict:
    """Route user commands to the appropriate handler or state change."""
    intent = state.get("classified_intent")

    if intent == "command_silence":
        return {
            "mode": "silenced",
            "pending_actions": [{"tool": "silence_alerts", "args": {}}],
        }

    if intent == "command_status":
        return {"classified_intent": "query"}

    if intent == "command_help":
        return {
            "notification_payload": {
                "nivel": "info",
                "razonamiento": (
                    "Comandos disponibles: /entendido (silenciar alertas), "
                    "/status (ver estado), /ayuda (este mensaje). "
                    "También podés preguntar por sensores o dar órdenes directas."
                ),
            },
            "notification_ready": True,
        }

    return {}


async def query_handler_node(state: SmartHomeState) -> dict:
    """Fetch sensor data via MCP and use LLM to generate a natural-language response."""
    mcp_client = MCPClient(url=settings.mcp_server_url)

    try:
        sensor_data = await mcp_client.call_tool("get_sensor_state")
        system_data = await mcp_client.call_tool("get_system_status")
    except Exception as exc:
        logger.warning("MCP call failed in query_handler_node: %s", exc)
        return {
            "error_type": "mcp_unreachable",
            "notification_payload": {
                "nivel": "error",
                "razonamiento": (
                    "No se pudo obtener el estado del sistema. "
                    "Intentá de nuevo en unos segundos."
                ),
            },
            "notification_ready": True,
        }

    temp = sensor_data.get("temperatura", sensor_data.get("temperature", "N/A"))
    hum = sensor_data.get("humedad", sensor_data.get("humidity", "N/A"))
    gas = sensor_data.get("gas", sensor_data.get("gas_ppm", "N/A"))
    sound = sensor_data.get("sonido", sensor_data.get("sound_db", "N/A"))

    user_question = state.get("user_input_raw", "¿Cómo está la casa?")

    # ── Check if user is asking about history ──
    raw_lower = user_question.lower()
    history_keywords = {"historial", "histórico", "historia", "ayer", "antes", "tendencia", "evolución"}
    if any(kw in raw_lower for kw in history_keywords):
        try:
            history_data = await mcp_client.call_tool("query_history", {"limit": 10})
        except Exception:
            history_data = None

        history_text = ""
        if history_data and isinstance(history_data, list) and len(history_data) > 0:
            entries = history_data[:5]
            history_text = "Últimas lecturas: " + "; ".join(
                f"{e.get('timestamp','?')[:16]}: T={e.get('temperatura','?')}°C G={e.get('gas','?')}ppm"
                for e in entries
            )
        else:
            history_text = "No hay datos históricos disponibles aún."

        return {
            "notification_payload": {"nivel": "info", "razonamiento": history_text},
            "notification_ready": True,
        }

    # ── Check if user is asking about system status ──
    status_keywords = {"estado del sistema", "sistema", "alertas activas", "led estado"}
    if any(kw in raw_lower for kw in status_keywords):
        status_text_parts = []
        if system_data:
            for k, v in system_data.items():
                status_text_parts.append(f"{k}: {v}")
        status_text = "; ".join(status_text_parts) if status_text_parts else "Estado del sistema no disponible."
        return {
            "notification_payload": {"nivel": "info", "razonamiento": status_text},
            "notification_ready": True,
        }

    # ── Normal query → LLM natural language ──

    # Build prompt for LLM
    user_prompt = (
        f"El usuario preguntó: \"{user_question}\"\n\n"
        f"Datos actuales de los sensores:\n"
        f"- Temperatura: {temp}°C\n"
        f"- Humedad: {hum}%\n"
        f"- Gas: {gas} ppm\n"
        f"- Ruido: {sound} dB\n\n"
        f"Respondé en español en lenguaje natural, en una o dos frases. "
        f"Si hay algo fuera de lo normal, avisá."
    )

    # Lazy import to avoid circular deps (same pattern as deciding_node)
    from ..ollama_client import OllamaClient, OllamaError
    from ..config import Settings

    _settings = Settings()
    try:
        ollama = OllamaClient(
            base_url=_settings.OLLAMA_URL,
            model=_settings.OLLAMA_MODEL,
            timeout=_settings.OLLAMA_TIMEOUT,
            max_retries=1,
        )
        raw = await asyncio.wait_for(ollama.generate(user_prompt, format_json=False), timeout=60.0)
        await ollama.close()
        response_text = raw.strip()
    except (asyncio.TimeoutError, OllamaError, Exception) as exc:
        logger.warning("LLM query failed in query_handler_node: %s", exc)
        # Fallback: raw sensor data
        response_text = (
            f"Temperatura: {temp}°C, Humedad: {hum}%, "
            f"Gas: {gas} ppm, Ruido: {sound} dB."
        )

    return {
        "notification_payload": {
            "nivel": "info",
            "razonamiento": response_text,
        },
        "notification_ready": True,
    }


async def direct_exec_node(state: SmartHomeState) -> dict:
    """Parse direct action keywords from the user message and map to MCP tools."""
    raw = state.get("user_input_raw", "").lower()
    action = None

    # LED alerta
    if _has_any(raw, {"prende", "prender", "enciende", "encender", "activa", "activar"}) and "led" in raw and "alerta" in raw:
        action = {"tool": "activate_led_alerta", "args": {"estado": True}}
    elif _has_any(raw, {"apaga", "apagar", "desactiva", "desactivar"}) and "led" in raw and "alerta" in raw:
        action = {"tool": "activate_led_alerta", "args": {"estado": False}}
    # LED puerta
    elif _has_any(raw, {"abre", "abrir", "prende", "prender", "activa", "activar"}) and ("puerta" in raw or "led puerta" in raw):
        action = {"tool": "activate_led_puerta", "args": {"accion": "ON"}}
    elif _has_any(raw, {"cierra", "cerrar", "apaga", "apagar", "desactiva", "desactivar"}) and ("puerta" in raw or "led puerta" in raw):
        action = {"tool": "activate_led_puerta", "args": {"accion": "OFF"}}
    # Cámara
    elif _has_any(raw, {"cámara", "camara", "foto", "captura", "capturar", "graba", "grabar", "fotografía", "fotografiar"}):
        action = {"tool": "trigger_camera", "args": {"duracion": 5}}
    # Notificación
    elif _has_any(raw, {"notifica", "notificar", "avisa", "avisar", "informa", "informar"}):
        action = {"tool": "send_notification", "args": {"mensaje": "Alerta enviada desde el agente SmartHome."}}
    # Silenciar alarmas
    elif _has_any(raw, {"silencia", "silenciar", "silencio"}):
        action = {"tool": "silence_alerts", "args": {}}
    else:
        return {}

    return {"pending_actions": [action]}


def _has_any(text: str, keywords: set) -> bool:
    """Check if any of the keywords appear as whole words in the text."""
    tokens = set(text.split())
    return bool(tokens & keywords)


async def waiting_confirmation_node(state: SmartHomeState) -> dict:
    """Ask the user to confirm a pending action before execution."""
    pending = state.get("pending_actions", [])
    action_str = ", ".join(a.get("tool", "acción") for a in pending) if pending else "acción"

    return {
        "needs_confirmation": True,
        "notification_payload": {
            "nivel": "confirm",
            "razonamiento": (
                f"Se requiere confirmación para ejecutar: {action_str}. "
                "Respondé 'sí' para confirmar o 'no' para cancelar."
            ),
        },
        "notification_ready": True,
    }


async def waiting_clarification_node(state: SmartHomeState) -> dict:
    """Request clarification from the user; give up after 3 attempts."""
    clarification_count = state.get("clarification_count", 0) + 1

    if clarification_count > 2:
        return {
            "classified_intent": "ambiguous",
            "clarification_asked": False,
            "clarification_count": clarification_count,
        }

    return {
        "clarification_asked": True,
        "clarification_count": clarification_count,
        "notification_payload": {
            "nivel": "clarify",
            "razonamiento": (
                "No entendí bien tu mensaje. ¿Podés reformularlo? "
                "Por ejemplo: 'prendé led alerta', '¿qué temperatura hay?' o '/status'."
            ),
        },
        "notification_ready": True,
    }


async def silenced_node(state: SmartHomeState) -> dict:
    """Silenced state: suppress alerts unless critical thresholds are breached."""
    gas_ppm = state.get("gas_ppm", 0)
    temperature = state.get("temperature", 0.0)

    if gas_ppm > 1020 or temperature > 30:
        return {
            "critical_active": True,
            "mode": "active",
        }

    mcp_client = MCPClient(url=settings.mcp_server_url)
    try:
        await mcp_client.call_tool("silence_alerts")
    except Exception as exc:
        logger.warning("MCP call failed in silenced_node: %s", exc)
        return {
            "error_type": "mcp_execution_fail",
            "retry_count": state.get("retry_count", 0) + 1,
        }

    normal_readings = state.get("normal_readings", 0) + 1
    result: dict = {
        "normal_readings": normal_readings,
        "notification_payload": {
            "nivel": "info",
            "razonamiento": "Alertas silenciadas. Respondé con /status para ver el estado.",
        },
        "notification_ready": True,
    }

    if normal_readings >= 3:
        result["mode"] = "active"

    return result
