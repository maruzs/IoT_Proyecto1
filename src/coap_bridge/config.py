from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for the CoAP Bridge microservice.

    All values are loaded from environment variables with sensible defaults.
    """

    MQTT_BROKER: str = "mosquitto"
    MQTT_PORT: int = 8883
    MQTT_USER: str = "coap-bridge-equipo69"
    MQTT_PASS: str = ""
    MQTT_TLS: bool = True
    MQTT_CA_CERT: str = "/certs/ca.crt"

    EQUIPO_ID: str = "equipo69"
    COAP_PORT: int = 5683

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
