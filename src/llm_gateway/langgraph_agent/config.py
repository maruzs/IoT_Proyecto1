from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Agent-specific settings loaded with AGENT_ prefix."""

    model_config = SettingsConfigDict(env_prefix="AGENT_", extra="ignore")

    mcp_server_url: str = "https://mcp-server:8002/mcp"
    agent_interval: int = 30
    critical_gas_threshold: int = 1020
    critical_temp_threshold: float = 30.0
    llm_timeout: int = 3
    mcp_max_retries: int = 3
    mcp_timeout: int = 5
