FROM python:3.11-slim

WORKDIR /app

# Copy digital-twin source as a package so relative imports resolve
COPY src/digital_twin/requirements.txt ./digital_twin/
RUN pip install --no-cache-dir -r ./digital_twin/requirements.txt

COPY src/digital_twin/ ./digital_twin/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "digital_twin.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
