import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import json_validator, prompt_builder
from ..api.schemas import (
    AgentRequest,
    AgentResponse,
    AgentErrorResponse,
    AgentDecision,
    AgentStateSummary,
    DecideRequest,
    DecideResponse,
    ErrorResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from ..langgraph_agent.graph import agent_with_user
from ..ollama_client import OllamaError

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_clients(request: Request):
    """Extract shared Ollama and MQTT clients from app.state.

    Raises HTTPException if clients are missing (should never happen after startup).
    """
    ollama = getattr(request.app.state, "ollama", None)
    mqtt = getattr(request.app.state, "mqtt", None)
    if ollama is None:
        raise HTTPException(status_code=500, detail="Ollama client not initialized")
    return ollama, mqtt


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    """Check connectivity to Ollama and MQTT."""
    ollama, mqtt = _get_clients(request)

    ollama_status: str = "unreachable"
    try:
        # Minimal ping to Ollama via a trivial generate call
        await ollama.generate("ping")
        ollama_status = "connected"
    except OllamaError:
        logger.warning("Ollama health check failed")
    except Exception:
        logger.exception("Unexpected error during Ollama health check")

    mqtt_status: str = "disconnected"
    try:
        if mqtt.is_connected():
            mqtt_status = "connected"
    except Exception:
        logger.exception("Unexpected error during MQTT health check")

    status: str = "healthy" if ollama_status == "connected" and mqtt_status == "connected" else "degraded"
    http_status = 200 if status == "healthy" else 503

    response = HealthResponse(
        status=status,  # type: ignore[arg-type]
        ollama=ollama_status,  # type: ignore[arg-type]
        mqtt=mqtt_status,  # type: ignore[arg-type]
    )
    return JSONResponse(
        content=response.model_dump(),
        status_code=http_status,
    )


@router.post("/llm/query", response_model=QueryResponse)
async def llm_query(request: Request, body: QueryRequest):
    """Send a free-form prompt to Ollama and return the raw response."""
    ollama, _ = _get_clients(request)

    try:
        raw = await ollama.generate(body.prompt)
    except OllamaError as exc:
        logger.error("Ollama query failed: %s", exc)
        raise HTTPException(
            status_code=504,
            detail=ErrorResponse(
                error="Ollama request timed out",
                detail=str(exc),
            ).model_dump(),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during Ollama query")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error="Ollama service unavailable",
                detail=str(exc),
            ).model_dump(),
        ) from exc

    parsed = json_validator.extract_json(raw)
    return QueryResponse(response=parsed, raw=raw)


@router.post("/llm/decide", response_model=DecideResponse)
async def llm_decide(request: Request, body: DecideRequest):
    """Build a decision prompt from sensor context, query Ollama, validate JSON, and publish to MQTT."""
    ollama, mqtt = _get_clients(request)

    user_prompt, system_prompt = prompt_builder.build_decision_prompt(body.sensor_context)

    try:
        raw = await ollama.generate(user_prompt, system_prompt)
    except OllamaError as exc:
        logger.error("Ollama decision failed: %s", exc)
        raise HTTPException(
            status_code=504,
            detail=ErrorResponse(
                error="Ollama request timed out",
                detail=str(exc),
            ).model_dump(),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during Ollama decision")
        raise HTTPException(
            status_code=502,
            detail=ErrorResponse(
                error="Ollama service unavailable",
                detail=str(exc),
            ).model_dump(),
        ) from exc

    try:
        decision = await json_validator.validate_and_parse(
            ollama_client=ollama,
            raw_text=raw,
            correction_prompt="The previous response was not valid JSON. Please correct it.",
            max_retries=3,
        )
    except json_validator.JsonValidationError as exc:
        logger.error("JSON validation failed after retries: %s", exc)
        # Publish error state to MQTT so subscribers know the decision failed
        try:
            if mqtt and mqtt.is_connected():
                error_payload = {
                    "error": "json_validation_failed",
                    "detail": str(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                mqtt.publish("llm/respuesta", error_payload)
        except Exception:
            logger.exception("Failed to publish error state to MQTT")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="LLM response could not be parsed as JSON",
                detail=raw,
            ).model_dump(),
        ) from exc

    mqtt_published = False
    try:
        if mqtt.is_connected():
            payload = {
                **decision,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            mqtt_published = mqtt.publish("llm/decision", payload)
        else:
            logger.warning("MQTT not connected — decision not published")
    except Exception:
        logger.exception("MQTT publish failed")

    return DecideResponse(decision=decision, mqtt_published=mqtt_published)


@router.post("/llm/agent", response_model=AgentResponse)
async def llm_agent(request: Request, body: AgentRequest):
    """Run the LangGraph agent with a user message.

    If sensor_override is provided, those values are injected into the initial state.
    The agent processes the message through the full state machine and returns
    the decision with notification payload.
    """
    ollama, mqtt = _get_clients(request)

    # Build initial state
    initial_state = {
        "user_input_raw": body.message,
        "sensor_stale": False,
        "mode": "active",
        "normal_readings": 0,
        "retry_count": 0,
        "max_retries": 3,
        "cycle_count": 0,
        "mcp_connected": True,
        "llm_available": True,
        "critical_active": False,
    }

    # Inject sensor override if provided (for testing or external triggers)
    if body.sensor_override:
        for key in ("temperature", "humidity", "gas_ppm", "sound_db"):
            if key in body.sensor_override:
                initial_state[key] = body.sensor_override[key]

    try:
        # Invoke the graph with a 30s timeout
        config = {"configurable": {"thread_id": f"user-{datetime.now(timezone.utc).timestamp()}"}}
        result = await asyncio.wait_for(
            agent_with_user.ainvoke(initial_state, config),
            timeout=180.0,
        )
    except asyncio.TimeoutError:
        logger.error("Agent graph timed out")
        raise HTTPException(
            status_code=504,
            detail=AgentErrorResponse(
                error_type="graph_timeout",
                detail="LangGraph agent did not complete within 180 seconds",
            ).model_dump(),
        )
    except Exception as exc:
        logger.exception("Agent graph execution failed")
        raise HTTPException(
            status_code=500,
            detail=AgentErrorResponse(
                error_type="graph_error",
                detail=str(exc),
            ).model_dump(),
        )

    # ── MQTT Wiring ──
    # Publish notification if the agent produced one
    notification = result.get("notification_payload")
    mqtt_published = False
    if notification and mqtt and mqtt.is_connected():
        try:
            mqtt.publish("llm/decision", notification)
            mqtt_published = True
        except Exception:
            logger.exception("Failed to publish agent notification to MQTT")

    # Build response
    decision_data = None
    llm_decision = result.get("llm_decision")
    if llm_decision:
        decision_data = AgentDecision(
            nivel=llm_decision.get("nivel", "info"),
            razonamiento=llm_decision.get("razonamiento", ""),
            acciones=llm_decision.get("acciones", llm_decision.get("actions", [])),
            confidence=llm_decision.get("confidence", 1.0),
            timestamp=datetime.now(timezone.utc),
        )

    state_data = AgentStateSummary(
        mode=result.get("mode", "active"),
        cycle_count=result.get("cycle_count", 0),
        sensor_stale=result.get("sensor_stale", False),
        mcp_connected=result.get("mcp_connected", True),
    )

    return AgentResponse(
        status="success",
        decision=decision_data,
        state=state_data,
        notification=notification,
        needs_confirmation=result.get("needs_confirmation", False),
    )
