import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm_gateway.langgraph_agent.graph import agent, agent_with_user
from src.llm_gateway.langgraph_agent.intent_classifier import classify
from src.llm_gateway.langgraph_agent.mcp_client import MCPClient
from src.llm_gateway.langgraph_agent.nodes import deciding_node


# ──────────────────────────────────────────────────────────────
# T-009.5.1 — Critical bypass path
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_critical_bypass_gas(mock_mcp_client, base_state):
    """Gas > 1020 ppm triggers immediate deterministic action — NO LLM call."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 25.0, "humidity": 50.0, "gas_ppm": 1100, "sound_db": 30.0}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    with patch("src.llm_gateway.ollama_client.OllamaClient") as mock_ollama:
        mock_ollama.return_value.generate = AsyncMock(return_value="{}")
        config = {"configurable": {"thread_id": "test-critical-gas"}}
        result = await agent.ainvoke(base_state, config)
        mock_ollama.return_value.generate.assert_not_called()

    assert result["critical_active"] is True
    assert result["llm_decision"]["nivel"] == "critico"
    assert result["llm_decision"]["confidence"] == 1.0
    actions = result["llm_decision"]["acciones"]
    assert any(a["tool"] == "activate_led_alerta" for a in actions)
    assert any(a["tool"] == "send_notification" for a in actions)
    assert any(a["tool"] == "trigger_camera" for a in actions)
    assert result["notification_payload"]["nivel"] == "critico"
    assert "gas" in result["notification_payload"]["razonamiento"].lower()


@pytest.mark.asyncio
async def test_critical_bypass_temp(mock_mcp_client, base_state):
    """Temp > 30°C triggers immediate deterministic action — NO camera."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 32.0, "humidity": 50.0, "gas_ppm": 200, "sound_db": 30.0}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    with patch("src.llm_gateway.ollama_client.OllamaClient") as mock_ollama:
        mock_ollama.return_value.generate = AsyncMock(return_value="{}")
        config = {"configurable": {"thread_id": "test-critical-temp"}}
        result = await agent.ainvoke(base_state, config)
        mock_ollama.return_value.generate.assert_not_called()

    assert result["critical_active"] is True
    assert result["llm_decision"]["nivel"] == "critico"
    actions = result["llm_decision"]["acciones"]
    assert any(a["tool"] == "activate_led_alerta" for a in actions)
    assert any(a["tool"] == "send_notification" for a in actions)
    assert not any(a["tool"] == "trigger_camera" for a in actions)


# ──────────────────────────────────────────────────────────────
# T-009.5.2 — Intent classifier accuracy
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "message,expected_intent",
    [
        ("/entendido", "command_silence"),
        ("/status", "command_status"),
        ("/ayuda", "command_help"),
        ("sí", "response_confirm"),
        ("no", "response_reject"),
        ("prendé LED alerta", "direct_action"),
        ("¿qué temperatura hay?", "query"),
        ("¿cómo está el gas?", "query"),
        ("activá la cámara", "direct_action"),
        ("hola", "ambiguous"),
    ],
)
def test_intent_classifier_accuracy(message, expected_intent):
    """Rule-first classifier must hit ≥85% without LLM calls."""
    with patch(
        "src.llm_gateway.langgraph_agent.intent_classifier.asyncio"
    ) as mock_asyncio:
        result = classify(message)
        assert result["intent"] == expected_intent
        # Ambiguous fallback has lower confidence; rules are 1.0
        if expected_intent == "ambiguous":
            assert result["confidence"] < 1.0
        else:
            assert result["confidence"] == 1.0
        # None of these should trigger the LLM fallback
        mock_asyncio.wait_for.assert_not_called()


# ──────────────────────────────────────────────────────────────
# T-009.5.3 — LLM timeout fallback + nested JSON handling
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_timeout_fallback(base_state):
    """3s LLM timeout → deterministic fallback by thresholds."""
    state = {**base_state, "gas_ppm": 900, "temperature": 29.0}

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(side_effect=asyncio.TimeoutError)
    result = await deciding_node(state, ollama_client=mock_ollama)
    mock_ollama.generate.assert_called_once()

    assert result["error_type"] == "llm_timeout"
    assert result["llm_decision"] is not None
    assert result["llm_decision"]["nivel"] in ("alto", "critico")
    assert len(result["pending_actions"]) > 0


@pytest.mark.asyncio
async def test_llm_nested_json_handling(base_state):
    """phi3:mini returns malformed nested JSON → graceful handling."""
    state = {**base_state}
    nested_response = (
        '{"nivel": "critico", "razonamiento": "Gas elevado", '
        '"acciones": [{"nombre": "led", "args": {"estado": true}}]}'
    )

    mock_ollama = AsyncMock()
    mock_ollama.generate = AsyncMock(return_value=nested_response)
    result = await deciding_node(state, ollama_client=mock_ollama)

    assert result["llm_decision"] is not None
    assert result["llm_decision"]["nivel"] == "critico"
    # The node normalizes acciones → actions and nombre → tool
    actions = result["llm_decision"]["acciones"]
    assert any(a["tool"] == "led" for a in actions)
    assert not any("nombre" in a for a in actions)


# ──────────────────────────────────────────────────────────────
# T-009.5.4 — MCP client tool calls (mocked server)
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_client_call_tool():
    """MCPClient successfully calls a tool and returns parsed result."""
    with patch(
        "src.llm_gateway.langgraph_agent.mcp_client.streamablehttp_client"
    ) as mock_transport:
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_transport.return_value.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write)
        )
        mock_transport.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.llm_gateway.langgraph_agent.mcp_client.ClientSession"
        ) as mock_session_cls:
            mock_session = mock_session_cls.return_value
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_session.initialize = AsyncMock()

            mock_result = MagicMock()
            mock_result.content = [MagicMock(text='{"temperature": 25.0}')]
            mock_session.call_tool = AsyncMock(return_value=mock_result)

            client = MCPClient(url="https://mock-mcp:8002/mcp")
            result = await client.call_tool("get_sensor_state")
            assert result == {"temperature": 25.0}


@pytest.mark.asyncio
async def test_mcp_client_connection_error():
    """MCPClient handles connection error gracefully."""
    with patch(
        "src.llm_gateway.langgraph_agent.mcp_client.streamablehttp_client"
    ) as mock_transport:
        mock_transport.side_effect = ConnectionError("MCP unreachable")

        client = MCPClient(url="https://mock-mcp:8002/mcp")
        with pytest.raises(ConnectionError):
            await client.call_tool("get_sensor_state")


# ──────────────────────────────────────────────────────────────
# T-009.5.5 — Integration: full autonomous cycles
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_autonomous_cycle_normal(mock_mcp_client, base_state):
    """Complete cycle: monitoring → evaluating → notifying (no anomaly)."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 25.0, "humidity": 50.0, "gas_ppm": 200, "sound_db": 30.0}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    with patch("src.llm_gateway.ollama_client.OllamaClient") as mock_ollama:
        mock_ollama.return_value.generate = AsyncMock(return_value="{}")
        config = {"configurable": {"thread_id": "test-normal"}}
        result = await agent.ainvoke(base_state, config)
        mock_ollama.return_value.generate.assert_not_called()

    assert result["notification_payload"] is not None
    assert result["notification_payload"]["nivel"] == "normal"
    assert not result.get("pending_actions")
    assert result["mode"] == "active"


@pytest.mark.asyncio
async def test_full_critical_cycle_end_to_end(mock_mcp_client, base_state):
    """Critical gas → immediate action → MQTT notification payload ready."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 25.0, "humidity": 50.0, "gas_ppm": 1100, "sound_db": 30.0}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    with patch("src.llm_gateway.ollama_client.OllamaClient") as mock_ollama:
        mock_ollama.return_value.generate = AsyncMock(return_value="{}")
        config = {"configurable": {"thread_id": "test-critical-e2e"}}
        result = await agent.ainvoke(base_state, config)
        mock_ollama.return_value.generate.assert_not_called()

    assert result["critical_active"] is True
    assert result["notification_payload"]["nivel"] == "critico"
    assert "gas" in result["notification_payload"]["razonamiento"].lower()

    # Verify executing_node called the right tools via MCP
    calls = mock_mcp_client.return_value.call_tool.call_args_list
    tool_names = [c.args[0] for c in calls]
    assert "activate_led_alerta" in tool_names
    assert "send_notification" in tool_names
    assert "trigger_camera" in tool_names


@pytest.mark.asyncio
async def test_full_llm_decision_cycle_end_to_end(mock_mcp_client, base_state, mock_ollama_client):
    """Anomalous but not critical → LLM decides → actions executed → MQTT payload ready."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 29.0, "humidity": 50.0, "gas_ppm": 450, "sound_db": 30.0}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    llm_response = (
        '{"nivel": "alto", "razonamiento": "Temperatura elevada con gas moderado", '
        '"acciones": [{"tool": "send_notification", "args": {"mensaje": "Alerta temp+gas"}}], '
        '"confidence": 0.9}'
    )
    mock_ollama_client.return_value.generate = AsyncMock(return_value=llm_response)

    config = {"configurable": {"thread_id": "test-llm-e2e"}}
    result = await agent.ainvoke(base_state, config)

    assert result["anomaly_detected"] is True
    assert result["llm_decision"]["nivel"] == "alto"
    assert result["notification_payload"]["nivel"] == "alto"
    assert "Temperatura elevada" in result["notification_payload"]["razonamiento"]

    # Verify send_notification was called via MCP
    calls = mock_mcp_client.return_value.call_tool.call_args_list
    tool_names = [c.args[0] for c in calls]
    assert "send_notification" in tool_names


@pytest.mark.asyncio
async def test_user_command_end_to_end(mock_mcp_client, base_state):
    """User sends /entendido → silenced → notification payload ready."""
    async def _side_effect(name, arguments=None):
        if name == "silence_alerts":
            return {"success": True}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    state = {**base_state, "user_input_raw": "/entendido"}
    config = {"configurable": {"thread_id": "test-user-cmd"}}
    result = await agent_with_user.ainvoke(state, config)

    assert result["classified_intent"] == "command_silence"
    assert result["mode"] == "silenced"

    # Verify silence_alerts was called via MCP
    calls = mock_mcp_client.return_value.call_tool.call_args_list
    tool_names = [c.args[0] for c in calls]
    assert "silence_alerts" in tool_names

    assert result["notification_payload"] is not None
    assert "silenciadas" in result["notification_payload"]["razonamiento"].lower()


@pytest.mark.asyncio
async def test_critical_overrides_silenced(mock_mcp_client, base_state):
    """Trace 4: Silenced mode + gas>1020 → critical override → immediate action → MQTT."""
    async def _side_effect(name, arguments=None):
        if name == "get_sensor_state":
            return {"temperature": 25.0, "humidity": 50.0, "gas_ppm": 1100, "sound_db": 30.0}
        if name == "activate_led_alerta":
            return {"success": True}
        if name == "send_notification":
            return {"success": True}
        if name == "trigger_camera":
            return {"success": True}
        return {"success": True}

    mock_mcp_client.return_value.call_tool.side_effect = _side_effect

    # Start in silenced mode with critical gas
    state = {**base_state, "mode": "silenced", "normal_readings": 1}
    config = {"configurable": {"thread_id": "test-silenced-override"}}
    result = await agent.ainvoke(state, config)

    # Silenced must be overridden — critical handler takes over
    assert result["critical_active"] is True
    assert result["llm_decision"]["nivel"] == "critico"
    assert result["llm_decision"]["confidence"] == 1.0  # deterministic, no LLM

    # Verify critical actions were called via MCP
    calls = mock_mcp_client.return_value.call_tool.call_args_list
    tool_names = [c.args[0] for c in calls]
    assert "activate_led_alerta" in tool_names
    assert "send_notification" in tool_names

    # MQTT payload must reflect the critical override
    assert result["notification_payload"] is not None
    assert result["notification_payload"]["nivel"] == "critico"
    assert "1100" in result["notification_payload"]["razonamiento"]


# ──────────────────────────────────────────────────────────────
# API endpoint MQTT verification (user explicit requirement)
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_llm_agent_endpoint_publishes_mqtt(mock_mqtt_instance):
    """POST /llm/agent publishes the graph notification to MQTT."""
    from fastapi import Request
    from src.llm_gateway.api.routes import llm_agent
    from src.llm_gateway.api.schemas import AgentRequest

    mock_request = MagicMock(spec=Request)
    mock_request.app.state.ollama = MagicMock()
    mock_request.app.state.mqtt = mock_mqtt_instance

    with patch("src.llm_gateway.api.routes.agent_with_user") as mock_agent:
        mock_agent.ainvoke = AsyncMock(return_value={
            "notification_payload": {
                "nivel": "normal",
                "razonamiento": "Todo en orden",
            },
            "llm_decision": {
                "nivel": "normal",
                "razonamiento": "Todo en orden",
                "acciones": [],
                "confidence": 1.0,
            },
            "mode": "active",
            "cycle_count": 1,
            "mcp_connected": True,
            "sensor_stale": False,
        })

        body = AgentRequest(message="¿cómo está todo?")
        response = await llm_agent(mock_request, body)

    assert response.status == "success"
    mock_mqtt_instance.publish.assert_called_once()
    topic, payload = mock_mqtt_instance.publish.call_args[0]
    assert topic == "llm/decision"
    assert payload["nivel"] == "normal"


@pytest.mark.asyncio
async def test_llm_agent_endpoint_critical_mqtt(mock_mqtt_instance):
    """POST /llm/agent with sensor override publishes critical decision to MQTT."""
    from fastapi import Request
    from src.llm_gateway.api.routes import llm_agent
    from src.llm_gateway.api.schemas import AgentRequest

    mock_request = MagicMock(spec=Request)
    mock_request.app.state.ollama = MagicMock()
    mock_request.app.state.mqtt = mock_mqtt_instance

    with patch("src.llm_gateway.api.routes.agent_with_user") as mock_agent:
        mock_agent.ainvoke = AsyncMock(return_value={
            "notification_payload": {
                "nivel": "critico",
                "razonamiento": "Gas 1100 ppm — umbral crítico",
            },
            "llm_decision": {
                "nivel": "critico",
                "razonamiento": "Gas 1100 ppm — umbral crítico",
                "acciones": [
                    {"tool": "activate_led_alerta", "args": {"estado": True}}
                ],
                "confidence": 1.0,
            },
            "mode": "active",
            "cycle_count": 1,
            "mcp_connected": True,
            "sensor_stale": False,
        })

        body = AgentRequest(
            message="evaluá ahora",
            sensor_override={"gas_ppm": 1100, "temperature": 35},
        )
        response = await llm_agent(mock_request, body)

    assert response.status == "success"
    assert response.decision.nivel == "critico"
    mock_mqtt_instance.publish.assert_called_once()
    topic, payload = mock_mqtt_instance.publish.call_args[0]
    assert topic == "llm/decision"
    assert payload["nivel"] == "critico"
    assert "gas" in payload["razonamiento"].lower()
