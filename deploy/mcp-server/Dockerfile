FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY deploy/mcp-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY deploy/mcp-server/ /app/

# Ensure /app is on PYTHONPATH for absolute imports
ENV PYTHONPATH=/app

# Generate mcp-server certificate using existing CA
COPY deploy/mosquitto/certs/ca.crt deploy/mosquitto/certs/ca.key /tmp/ca/
RUN mkdir -p /certs && \
    openssl genrsa -out /certs/mcp-server.key 2048 && \
    openssl req -new -key /certs/mcp-server.key -out /tmp/mcp-server.csr \
        -subj "/C=AR/O=SmartHomeIoT/CN=mcp-server" && \
    printf "subjectAltName=DNS:mcp-server,DNS:localhost" > /tmp/mcp-server.ext && \
    openssl x509 -req -in /tmp/mcp-server.csr \
        -CA /tmp/ca/ca.crt -CAkey /tmp/ca/ca.key -CAcreateserial \
        -out /certs/mcp-server.crt -days 365 -extfile /tmp/mcp-server.ext && \
    rm -f /tmp/mcp-server.csr /tmp/mcp-server.ext /tmp/ca/ca.srl && \
    chmod 644 /certs/mcp-server.crt && \
    chmod 600 /certs/mcp-server.key

EXPOSE 8002

ENTRYPOINT ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--ssl-certfile", "/certs/mcp-server.crt", "--ssl-keyfile", "/certs/mcp-server.key"]
