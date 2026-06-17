from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    prompt: str


class QueryResponse(BaseModel):
    response: dict | None
    raw: str


class DecideRequest(BaseModel):
    sensor_context: dict


class DecideResponse(BaseModel):
    decision: dict
    mqtt_published: bool


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    ollama: Literal["connected", "unreachable"]
    mqtt: Literal["connected", "disconnected"]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class AgentRequest(BaseModel):
    message: str
    sensor_override: Optional[dict] = None
    skip_llm: bool = False


class AgentDecision(BaseModel):
    nivel: str
    razonamiento: str
    acciones: list[dict] = []
    confidence: float
    timestamp: datetime


class AgentStateSummary(BaseModel):
    mode: str
    cycle_count: int
    sensor_stale: bool = False
    mcp_connected: bool = True


class AgentResponse(BaseModel):
    status: str = "success"  # "success" | "error"
    decision: Optional[AgentDecision] = None
    state: Optional[AgentStateSummary] = None
    notification: Optional[dict] = None  # raw notification payload for frontend display


class AgentErrorResponse(BaseModel):
    status: str = "error"
    detail: str
    error_type: str
