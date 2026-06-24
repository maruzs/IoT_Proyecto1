from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# --- Command patterns (exact match on first word) ---
_COMMAND_SILENCE = {"/entendido", "/ok", "/silenciar", "/silencio"}
_COMMAND_STATUS = {"/status", "/estado"}
_COMMAND_HELP = {"/help", "/ayuda"}

# --- Response confirmations (short responses) ---
_CONFIRM_WORDS = {"sí", "si", "dale", "ok", "confirmo", "aprobado"}
_REJECT_WORDS = {"no", "nop", "cancelar", "rechazo"}

# --- Direct action keywords (español neutro: imperativo + infinitivos) ---
_ACTION_KEYWORDS = {
    # Encender / apagar
    "prende", "prender", "enciende", "encender",
    "apaga", "apagar",
    # Activar / desactivar
    "activa", "activar", "desactiva", "desactivar",
    # Silenciar
    "silencia", "silenciar",
    # Puerta
    "abre", "abrir", "cierra", "cerrar",
    # Cámara — mirar, ver, fijarse
    "captura", "capturar", "graba", "grabar", "foto", "fotografía", "fotografiar",
    "mira", "mirá", "mirar", "ve", "ver", "fijate", "fíjate", "fijarse",
    "revisa", "revisar", "chequea", "chequear", "comprueba", "comprobar",
    "verifica", "verificar", "inspecciona", "inspeccionar",
    # Notificación
    "notifica", "notificar", "avisa", "avisar", "informa", "informar",
}

# --- Query keywords ---
_QUERY_KEYWORDS = {
    "qué", "cuál", "cómo", "cuánto", "donde",
    "hay", "está", "estan",
    "temperatura", "humedad", "gas", "ruido", "sonido",
    "estado", "led", "alerta", "cámara", "sensor", "sensores",
    "historial", "histórico", "historia", "ayer", "antes", "tendencia",
    "nivel", "valor", "valores", "lectura", "datos",
    "registro", "hoy", "pasó", "paso", "último", "ultimo",
    "mostrame", "mostrar", "decime", "decir",
    "calor", "frío", "frio", "fresco", "cálido", "calido",
    "seguro", "peligro", "riesgo", "normal", "bien", "mal",
}

# Strip punctuation for normalization
_PUNCT_RE = re.compile(r"[¿?¡!.,;:\-\"'()\[\]{}]+")


def _normalize(text: str) -> str:
    """Lowercase and strip surrounding whitespace."""
    return text.strip().lower()


def _first_word(text: str) -> str:
    """Return the first whitespace-separated token."""
    return text.split(None, 1)[0] if text else ""


def _tokens(text: str) -> set[str]:
    """Return a set of normalized tokens (punctuation removed)."""
    cleaned = _PUNCT_RE.sub(" ", text)
    return set(cleaned.split())


async def classify(message: str, ollama_client: Optional[object] = None) -> dict:
    """Classify a user message using a rule-first approach.

    Rules are evaluated in priority order. Only ambiguous messages
    that match no rule are sent to the LLM fallback.

    Returns:
        {"intent": str, "confidence": float, "entities": dict}
    """
    raw = _normalize(message)
    if not raw:
        return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}

    # 1. Commands — exact match on first word
    first = _first_word(raw)
    if first in _COMMAND_SILENCE:
        return {"intent": "command_silence", "confidence": 1.0, "entities": {}}
    if first in _COMMAND_STATUS:
        return {"intent": "command_status", "confidence": 1.0, "entities": {}}
    if first in _COMMAND_HELP:
        return {"intent": "command_help", "confidence": 1.0, "entities": {}}

    # 2. Response confirmations / rejections — message is a standalone yes/no
    #    Only trigger when confirmation/rejection words DOMINATE the message
    #    (prevents "fijate si hay alguien" from being misclassified as confirmation)
    tokens_set = _tokens(raw)
    conf_rej_tokens = _CONFIRM_WORDS | _REJECT_WORDS
    conf_rej_overlap = tokens_set & conf_rej_tokens
    if conf_rej_overlap and len(conf_rej_overlap) >= len(tokens_set) * 0.5:
        if tokens_set & _CONFIRM_WORDS:
            return {"intent": "response_confirm", "confidence": 1.0, "entities": {}}
        if tokens_set & _REJECT_WORDS:
            return {"intent": "response_reject", "confidence": 1.0, "entities": {}}

    # 3. Direct actions — action keywords anywhere in the message (checked BEFORE queries
    #    because some action targets appear in query keywords: "led", "cámara", "alerta")
    if tokens_set & _ACTION_KEYWORDS:
        return {"intent": "direct_action", "confidence": 1.0, "entities": {}}

    # 4. Queries — question keywords or message ends with '?' (but NOT if matched as action)
    if raw.endswith("?") or (tokens_set & _QUERY_KEYWORDS):
        return {"intent": "query", "confidence": 1.0, "entities": {}}

    # 5. LLM fallback — deduce intent AND action when no rule matches
    if ollama_client is not None:
        return await _llm_deduce(message, ollama_client)

    return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}


async def _llm_deduce(message: str, ollama_client) -> dict:
    """Ask the LLM to deduce the user's intent and the corresponding MCP tool + args."""
    system_prompt = (
        "Sos un clasificador de intenciones para un sistema SmartHome (equipo69).\n"
        "Tu única tarea es clasificar el mensaje del usuario en UNA categoría "
        "y devolver la herramienta MCP correspondiente.\n\n"
        "⚠️ REGLA PRINCIPAL: si el usuario pide VER, REVISAR, COMPROBAR, INSPECCIONAR "
        "o FIJARSE si hay alguien en la puerta/entrada, la intención ES 'direct_action' "
        "y la herramienta ES 'trigger_camera'. No importa que haya palabras interrogativas "
        "en la frase — el usuario quiere una acción, no una consulta.\n\n"
        "Contexto del sistema — qué hace cada sensor:\n"
        "- Temperatura y humedad: miden el ambiente general de la casa.\n"
        "- Gas (MQ-2): detecta concentración de gas en el aire de la casa.\n"
        "- Ruido (MAX4466): micrófono cerca de la puerta, detecta golpes, timbre, "
        "voces, movimiento cerca de la entrada.\n"
        "- Cámara (ESP32-CAM): apunta a la puerta, hace reconocimiento facial. "
        "Se activa con trigger_camera(duracion) para ver quién está en la puerta.\n"
        "- LED alerta: señal visual de emergencia (gas/temperatura críticos).\n"
        "- LED puerta: indica si la puerta está abierta o cerrada.\n\n"
        "Herramientas disponibles:\n"
        "- activate_led_alerta(estado: bool) — encender/apagar LED de alerta\n"
        "- activate_led_puerta(accion: ON/OFF) — abrir/cerrar puerta\n"
        "- trigger_camera(duracion: int) — activar cámara para ver quién está en la puerta\n"
        "- send_notification(mensaje: str) — enviar notificación por Telegram\n"
        "- silence_alerts() — silenciar todas las alarmas\n"
        "- get_sensor_state() — leer todos los sensores (temp, hum, gas, ruido)\n"
        "- get_system_status() — estado de LEDs y alertas\n"
        "- query_history(from, to, limit) — consultar historial de lecturas\n\n"
        "Guía de clasificación por tipo de palabra:\n"
        "- Verbos de acción (prender, apagar, activar, abrir, cerrar, mirar, ver,\n"
        "  fijarse, revisar, chequear, comprobar, verificar, inspeccionar,\n"
        "  notificar, avisar, silenciar, capturar, grabar, fotografiar)\n"
        "  → intent='direct_action', tool=la herramienta que corresponda\n"
        "- Palabras interrogativas (qué, cuál, cómo, cuánto, dónde)\n"
        "  o términos de estado (temperatura, humedad, gas, ruido, estado,\n"
        "  historial, registro, nivel, seguro, peligro, calor, frío)\n"
        "  → intent='query', tool=get_sensor_state o get_system_status o query_history\n"
        "- Si el mensaje tiene TANTO una palabra de acción COMO una interrogativa,\n"
        "  ganan los verbos de acción → intent='direct_action'\n"
        "- Comandos como /entendido, /status, /ayuda → intent='command'\n"
        "- Mensajes que no encajan claramente en ninguna categoría → intent='ambiguous'\n\n"
        "Respondé SOLO con este JSON exacto, sin explicaciones ni markdown:\n"
        '{"intent":"direct_action|query|command|ambiguous",'
        '"tool":"nombre_o_null","tool_args":{},"reasoning":"breve"}'
    )

    user_prompt = f'Mensaje del usuario: "{message}"'
    try:
        raw = await asyncio.wait_for(
            ollama_client.generate(user_prompt, system_prompt=system_prompt, format_json=True),
            timeout=120.0,
        )
        # Try to parse as JSON
        import json as _json
        # Strip markdown fences and fix common phi3:mini JSON quirks
        cleaned = raw.strip()
        # Remove ``` fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
            cleaned = cleaned.rsplit("```", 1)[0] if cleaned.endswith("```") else cleaned
            cleaned = cleaned.strip()
        # phi3:mini sometimes uses \\' which is not valid JSON
        cleaned = cleaned.replace("\\'", "'")
        data = _json.loads(cleaned)
        intent = data.get("intent", "ambiguous")
        if intent not in ("direct_action", "query", "command", "ambiguous"):
            intent = "ambiguous"
        return {
            "intent": intent,
            "confidence": 0.7,
            "entities": {
                "tool": data.get("tool"),
                "tool_args": data.get("tool_args"),
            },
        }
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("Intent classifier LLM fallback failed: %s (type=%s)", exc, type(exc).__name__)
        return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}
