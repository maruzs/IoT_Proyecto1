"""Digital Twin HTTP client — consume GET /gemelo/estado."""

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class DigitalTwinClient:
    """Async HTTP client for the Digital Twin REST API.

    The Digital Twin exposes a single consolidated endpoint:
      GET /gemelo/estado
    which returns estado_actual, historial_1h, alertas_activas,
    prediccion_30min, and resumen_llm.
    """

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def _get_full_state(self) -> Dict[str, Any]:
        url = f"{self.base_url}/gemelo/estado"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_sensor_state(self) -> Dict[str, Any]:
        """Return current sensor readings from the Digital Twin."""
        state = await self._get_full_state()
        return state.get("estado_actual", {})

    async def get_full_state(self) -> Dict[str, Any]:
        """Return the complete Digital Twin state."""
        return await self._get_full_state()

    async def get_alerts(self) -> list[str]:
        """Return list of active alerts."""
        state = await self._get_full_state()
        return state.get("alertas_activas", [])

    async def get_predictions(self) -> Dict[str, Any]:
        """Return 30-minute predictions if available."""
        state = await self._get_full_state()
        pred = state.get("prediccion_30min", {})
        return {k: v for k, v in pred.items() if v is not None}

    async def get_history(self) -> list[Dict[str, Any]]:
        """Return the last 60 history entries."""
        state = await self._get_full_state()
        return state.get("historial_1h", [])
