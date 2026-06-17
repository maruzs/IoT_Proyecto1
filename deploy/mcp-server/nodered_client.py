import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class NodeRedClient:
    """Async HTTP client for Node-RED REST endpoints."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        response = await self.client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    async def get_sensor_state(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/sensors")

    async def get_system_status(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/status")

    async def query_history(
        self,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if from_time is not None:
            params["from"] = from_time
        if to_time is not None:
            params["to"] = to_time
        if limit is not None:
            params["limit"] = limit
        return await self._request("GET", "/api/history", params=params)

    async def activate_led_alerta(self, estado: bool) -> Dict[str, Any]:
        return await self._request("POST", "/api/actuators/led-alerta", json={"estado": estado})

    async def activate_led_puerta(self, accion: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/actuators/led-puerta", json={"accion": accion})

    async def send_notification(self, mensaje: str) -> Dict[str, Any]:
        return await self._request("POST", "/api/notifications", json={"mensaje": mensaje})

    async def silence_alerts(self) -> Dict[str, Any]:
        return await self._request("POST", "/api/alerts/silence")

    async def trigger_camera(self, duracion: int) -> Dict[str, Any]:
        return await self._request("POST", "/api/camera/trigger", json={"duracion": duracion})
