FROM python:3.11-slim

WORKDIR /app

# Copy bridge source as a package so relative imports resolve
COPY src/coap_bridge/requirements.txt ./coap_bridge/
RUN pip install --no-cache-dir -r ./coap_bridge/requirements.txt

COPY src/coap_bridge/ ./coap_bridge/

ENV PYTHONUNBUFFERED=1

EXPOSE 5683/udp

CMD ["python", "-m", "coap_bridge.main"]
