from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def base_state():
    """Minimal initial state for the LangGraph agent."""
    return {
        "mode": "active",
        "normal_readings": 0,
        "retry_count": 0,
        "max_retries": 3,
        "cycle_count": 0,
        "mcp_connected": True,
        "llm_available": True,
        "critical_active": False,
        "sensor_stale": False,
    }


@pytest.fixture
def mock_mcp_client():
    """Mock MCPClient in nodes.py to return fake sensor data."""
    with patch("src.llm_gateway.langgraph_agent.nodes.MCPClient") as mock:
        instance = mock.return_value
        instance.call_tool = AsyncMock(
            return_value={
                "temperature": 25.0,
                "humidity": 50.0,
                "gas_ppm": 200,
                "sound_db": 30.0,
            }
        )
        yield mock


@pytest.fixture
def mock_ollama_client():
    """Mock OllamaClient at source module to intercept lazy import in deciding_node."""
    with patch("src.llm_gateway.ollama_client.OllamaClient") as mock:
        instance = mock.return_value
        instance.generate = AsyncMock(
            return_value='{"nivel": "normal", "razonamiento": "ok", "acciones": [], "confidence": 1.0}'
        )
        instance.close = AsyncMock()
        yield mock


@pytest.fixture
def mock_mqtt_publisher():
    """Mock MQTTPublisher class for routes.py tests."""
    with patch("src.llm_gateway.mqtt_client.MQTTPublisher") as mock:
        instance = mock.return_value
        instance.publish = MagicMock(return_value=True)
        instance.is_connected = MagicMock(return_value=True)
        yield instance


@pytest.fixture
def mock_mqtt_instance():
    """Standalone mock MQTT publisher instance for endpoint tests."""
    instance = MagicMock()
    instance.publish = MagicMock(return_value=True)
    instance.is_connected = MagicMock(return_value=True)
    return instance
