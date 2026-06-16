# =============================================================================
# Ollama — LLM Local para SmartHome IoT
# =============================================================================
# Modelo por defecto: phi3:mini (configurable vía OLLAMA_MODEL)
# API expuesta en :11434 — usada por el LLM Gateway y LangGraph Agent
# =============================================================================

FROM ollama/ollama:latest

EXPOSE 11434

COPY deploy/ollama/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
