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

# --- Direct action keywords ---
_ACTION_KEYWORDS = {"prendé", "apagá", "activá", "desactivá", "encendé", "silenciá"}

# --- Query keywords ---
_QUERY_KEYWORDS = {
    "qué", "cuál", "cómo", "cuánto", "hay", "está",
    "temperatura", "humedad", "gas", "ruido", "sonido",
    "estado", "led", "alerta", "cámara",
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


def classify(message: str, ollama_client: Optional[object] = None) -> dict:
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

    # 2. Response confirmations / rejections — short responses
    # Heuristic: message is short (≤30 chars) or consists only of confirmation/rejection words
    tokens_set = _tokens(raw)
    if len(raw) <= 30 or tokens_set.issubset(_CONFIRM_WORDS | _REJECT_WORDS):
        if tokens_set & _CONFIRM_WORDS:
            return {"intent": "response_confirm", "confidence": 1.0, "entities": {}}
        if tokens_set & _REJECT_WORDS:
            return {"intent": "response_reject", "confidence": 1.0, "entities": {}}

    # 3. Direct actions — action keywords anywhere in the message
    if tokens_set & _ACTION_KEYWORDS:
        return {"intent": "direct_action", "confidence": 1.0, "entities": {}}

    # 4. Queries — question keywords or message ends with '?'
    if raw.endswith("?") or (tokens_set & _QUERY_KEYWORDS):
        return {"intent": "query", "confidence": 1.0, "entities": {}}

    # 5. LLM fallback — only when no rule matches
    if ollama_client is not None:
        prompt = (
            "Clasificá este mensaje en UNA categoría: "
            "direct_action, query, command, contextual_action, ambiguous. "
            f"Mensaje: {message}. Categoría:"
        )
        try:
            result = asyncio.wait_for(
                ollama_client.generate(prompt),
                timeout=2.0,
            )
            # Normalize result to one of the expected intents
            intent = _normalize(str(result))
            valid_intents = {
                "direct_action",
                "query",
                "command",
                "contextual_action",
                "ambiguous",
            }
            if intent not in valid_intents:
                intent = "ambiguous"
            return {"intent": intent, "confidence": 0.7, "entities": {}}
        except asyncio.TimeoutError:
            logger.warning("Intent classifier LLM fallback timed out after 2s")
            return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}
        except Exception as exc:
            logger.warning("Intent classifier LLM fallback failed: %s", exc)
            return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}

    # No rules matched and no LLM client available
    return {"intent": "ambiguous", "confidence": 0.5, "entities": {}}
