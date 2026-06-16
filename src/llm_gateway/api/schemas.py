from typing import Literal

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
