from __future__ import annotations

from typing import TypedDict, Optional, Literal


class SmartHomeState(TypedDict, total=False):
    """Shared state for the LangGraph smart-home agent.

    All fields are optional so that the graph can start from a minimal
    dictionary and let each node add only what it needs.
    """

    # LangGraph convention — message history
    messages: list

    # Sensor fields
    temperature: float
    humidity: float
    gas_ppm: int
    sound_db: float
    sensor_ts: str
    sensor_stale: bool

    # Actuator fields
    led_alerta: bool
    led_puerta: Literal["ON", "OFF"]

    # System fields
    mcp_connected: bool
    llm_available: bool
    mode: Literal["active", "silenced", "degraded"]
    trigger: Literal["timer_30s", "user_message", "api_call"]

    # Counter fields
    normal_readings: int
    last_critical: Optional[str]
    critical_active: bool

    # LLM fields
    llm_decision: Optional[dict]
    anomaly_detected: bool
    trend_rising: bool

    # User interaction
    user_input_raw: str
    classified_intent: Optional[str]
    intent_confidence: float
    needs_confirmation: bool
    user_response: Optional[str]
    clarification_asked: bool
    clarification_count: int

    # Pending actions
    pending_actions: list
    action_plan: list
    mcp_results: list

    # Notification
    notification_payload: dict
    notification_ready: bool

    # Error handling
    error_type: Optional[str]
    retry_count: int
    max_retries: int
    degraded_since: Optional[str]

    # Timer
    last_evaluation_ts: str
    cycle_count: int
