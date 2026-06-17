from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the LLM Gateway microservice.

    All values are loaded from environment variables with sensible defaults.
    """

    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT: int = 30
    MAX_RETRIES: int = 3

    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 8883
    MQTT_USER: str = "equipo69"
    MQTT_PASS: str = ""
    MQTT_TLS: bool = True
    MQTT_CA_CERT: str = "/certs/ca.crt"

    EQUIPO_ID: str = "equipo69"

    # Agent configuration (T-009)
    MCP_SERVER_URL: str = "https://mcp-server:8002/mcp"
    AGENT_ENABLED: bool = True
    AGENT_INTERVAL: int = 30
    CRITICAL_GAS_THRESHOLD: int = 1020
    CRITICAL_TEMP_THRESHOLD: float = 30.0
    LLM_TIMEOUT: int = 3
    MCP_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
