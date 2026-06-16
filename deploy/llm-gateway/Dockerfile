FROM python:3.11-slim

WORKDIR /app

# Copy gateway source as a package so relative imports resolve
COPY src/llm_gateway/requirements.txt ./llm_gateway/
RUN pip install --no-cache-dir -r ./llm_gateway/requirements.txt

COPY src/llm_gateway/ ./llm_gateway/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "llm_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
