import json
from unittest import mock

import pytest
from starlette.testclient import TestClient

from main import app, mcp
from tools import _nodered_client

client = TestClient(app)


def test_health():
    """Smoke test: /health returns ok with nodered status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "nodered" in data
    assert data["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_tools_list():
    """Smoke test: MCP tools/list returns exactly 8 tools."""
    tools = await mcp.list_tools()
    assert len(tools) == 8
    names = {t.name for t in tools}
    expected = {
        "get_sensor_state",
        "get_system_status",
        "query_history",
        "activate_led_alerta",
        "activate_led_puerta",
        "send_notification",
        "silence_alerts",
        "trigger_camera",
    }
    assert names == expected


@pytest.mark.asyncio
async def test_get_sensor_state_integration():
    """Integration test: get_sensor_state forwards Node-RED response."""
    mock_data = {
        "temperatura": 22.5,
        "humedad": 60,
        "gas": 300,
        "sonido": 45,
    }
    with mock.patch.object(
        _nodered_client, "get_sensor_state", new_callable=mock.AsyncMock
    ) as m:
        m.return_value = mock_data
        result = await mcp.call_tool("get_sensor_state", {})
        # FastMCP wraps string returns as ([TextContent], meta)
        assert isinstance(result, tuple)
        contents = result[0]
        assert len(contents) == 1
        data = json.loads(contents[0].text)
        assert data["temperatura"] == 22.5
        assert data["humedad"] == 60


@pytest.mark.asyncio
async def test_error_mapping_503():
    """Integration test: Node-RED 503 maps to MCP error."""
    from httpx import HTTPStatusError, Response

    exc = HTTPStatusError(
        "Service Unavailable",
        request=mock.Mock(),
        response=Response(503, json={"error": "sensor_data_unavailable"}),
    )
    with mock.patch.object(
        _nodered_client, "get_sensor_state", new_callable=mock.AsyncMock
    ) as m:
        m.side_effect = exc
        with pytest.raises(Exception) as ctx:
            await mcp.call_tool("get_sensor_state", {})
        assert "unavailable" in str(ctx.value).lower()
