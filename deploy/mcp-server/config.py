from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    node_red_url: str = "http://nodered:1880"
    digital_twin_url: str = ""  # empty = use node_red_url
    mcp_port: int = 8002
    mcp_host: str = "0.0.0.0"
    log_level: str = "INFO"

    # TLS
    tls_cert: str = "/certs/mcp-server.crt"
    tls_key: str = "/certs/mcp-server.key"

    model_config = SettingsConfigDict(env_prefix="MCP_")


settings = Settings()
