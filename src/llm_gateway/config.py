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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
