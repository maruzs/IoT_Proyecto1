#!/bin/sh
set -e

MODEL="${OLLAMA_MODEL:-phi3:mini}"

echo "==> Starting Ollama serve in background..."
ollama serve &
OLLAMA_PID=$!

echo "==> Waiting for Ollama API to be ready..."
until ollama list > /dev/null 2>&1; do
    sleep 1
done

echo "==> Pulling model: ${MODEL}..."
ollama pull "${MODEL}"

echo "==> Ollama ready — model ${MODEL} loaded on port 11434"

# Keep ollama serve running in foreground
wait $OLLAMA_PID
