FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir paho-mqtt

COPY src/digital_twin/mqtt_to_influx.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "mqtt_to_influx.py"]
