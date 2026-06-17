import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .mqtt_client import DigitalTwinMQTTClient
from .predictor import predict_all_metrics
from .state_manager import StateManager

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("src.digital_twin")

app = FastAPI(title="SmartHome Digital Twin Service", version="1.0.0")

# Mode selection: "DEV_LOCAL" runs with mock generator and fast loops, "PROD" is normal operation
MODE = os.environ.get("MODE", "PROD").upper()

# Instantiate singleton managers
state_manager = StateManager()
mqtt_client = DigitalTwinMQTTClient(state_manager)

# Snapshot configuration
SNAPSHOT_PATH = os.environ.get("SNAPSHOT_PATH", "/app/data/twin_snapshot.json")

# Background task loops
background_tasks = set()


def save_snapshot() -> None:
    """Save the current state to a JSON snapshot file on disk."""
    state = state_manager.get_full_state()
    try:
        dir_name = os.path.dirname(SNAPSHOT_PATH)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        with open(SNAPSHOT_PATH, "w") as f:
            json.dump(state, f, indent=2)
        logger.debug("State snapshot saved successfully to %s", SNAPSHOT_PATH)
    except Exception as e:
        logger.error("Failed to save snapshot to %s: %s", SNAPSHOT_PATH, e)


def load_snapshot() -> None:
    """Load state from a JSON snapshot file on disk if it exists."""
    if os.path.exists(SNAPSHOT_PATH):
        try:
            with open(SNAPSHOT_PATH, "r") as f:
                data = json.load(f)
            state_manager.import_state(data)
            logger.info("Successfully restored state from snapshot: %s", SNAPSHOT_PATH)
        except Exception as e:
            logger.error("Failed to load snapshot from %s: %s", SNAPSHOT_PATH, e)
    else:
        logger.info("No snapshot found at %s. Starting with fresh state.", SNAPSHOT_PATH)


def run_prediction_and_publish() -> None:
    """Calculate linear regression predictions for temperature, humidity, and gas

    and publish them to MQTT.
    """
    logger.info("Triggering linear regression prediction calculations...")
    full_state = state_manager.get_full_state()
    history = full_state.get("historial_1h", [])

    # Predict using the predictor module (min 5 points required)
    temp_pred, hum_pred, gas_pred = predict_all_metrics(history, horizon_minutes=30.0, min_points=5)

    # Save to state manager
    state_manager.set_predictions(temp_pred, hum_pred, gas_pred)

    # Publish to MQTT if values are available (and MQTT is connected)
    if mqtt_client.client.is_connected():
        if temp_pred is not None:
            mqtt_client.publish_prediction("temperatura", temp_pred)
        if hum_pred is not None:
            mqtt_client.publish_prediction("humedad", hum_pred)
        if gas_pred is not None:
            mqtt_client.publish_prediction("gas", gas_pred)
    else:
        logger.debug("MQTT not connected — predictions not published to broker")


# ------------------------------------------------------------------ #
# Background Schedulers & Simulators
# ------------------------------------------------------------------ #


async def dev_telemetry_generator() -> None:
    """Generates mock telemetry data every second in DEV_LOCAL mode to test logic."""
    import random
    logger.info("Mock telemetry generator started.")
    
    # Starting seed values
    temp = 22.0
    hum = 55.0
    gas = 280.0
    
    try:
        while True:
            # Simulate a slow drift up/down
            temp += random.uniform(-0.15, 0.25)
            hum += random.uniform(-0.3, 0.2)
            gas += random.uniform(-5.0, 7.5)
            
            # Constrain values
            temp = max(15.0, min(38.0, temp))
            hum = max(30.0, min(90.0, hum))
            gas = max(100.0, min(600.0, gas))
            
            state_manager.update_sensor_readings(
                temp=temp,
                hum=hum,
                gas=gas,
                sensor_extra=random.uniform(20, 50)
            )
            await asyncio.sleep(1.0)
    except asyncio.CancelledError:
        logger.info("Mock telemetry generator stopped.")


async def minute_consolidation_loop() -> None:
    """Every 60 seconds (or 5 seconds in DEV_LOCAL), consolidate the readings into the history."""
    interval = 5 if MODE == "DEV_LOCAL" else 60
    logger.info("Consolidation loop starting with interval: %d seconds", interval)
    try:
        if MODE != "DEV_LOCAL":
            # Align roughly to the start of a minute boundary
            now = datetime.now()
            delay = 60 - now.second - (now.microsecond / 1_000_000.0)
            await asyncio.sleep(delay)

        while True:
            state_manager.consolidate_minute_average()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Minute consolidation loop stopped.")
    except Exception as e:
        logger.error("Error in minute consolidation loop: %s", e, exc_info=True)


async def prediction_scheduler_loop() -> None:
    """Every 10 minutes (or 15 seconds in DEV_LOCAL), calculate predictions and publish them."""
    interval = 15 if MODE == "DEV_LOCAL" else 600
    startup_delay = 5 if MODE == "DEV_LOCAL" else 30
    
    logger.info("Prediction scheduler loop starting (interval=%ds, startup_delay=%ds)", interval, startup_delay)
    try:
        await asyncio.sleep(startup_delay)
        while True:
            run_prediction_and_publish()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("Prediction scheduler loop stopped.")
    except Exception as e:
        logger.error("Error in prediction scheduler loop: %s", e, exc_info=True)


async def snapshot_scheduler_loop() -> None:
    """Every 30 seconds, save the state to disk."""
    try:
        while True:
            await asyncio.sleep(30)
            save_snapshot()
    except asyncio.CancelledError:
        logger.info("Snapshot scheduler loop stopped.")
    except Exception as e:
        logger.error("Error in snapshot scheduler loop: %s", e, exc_info=True)


# ------------------------------------------------------------------ #
# FastAPI Routes
# ------------------------------------------------------------------ #


@app.get("/health")
def health_check() -> JSONResponse:
    """Healthcheck endpoint checking MQTT connectivity."""
    mqtt_ok = mqtt_client.client.is_connected()
    status = "healthy" if mqtt_ok else "degraded"
    return JSONResponse(
        content={
            "status": status,
            "mqtt_connected": mqtt_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status_code=200 if mqtt_ok else 503,
    )


@app.get("/gemelo/estado")
def get_state() -> Dict[str, Any]:
    """Retrieve the complete current state, historical data, active alerts, and predictions."""
    return state_manager.get_full_state()


@app.post("/gemelo/predecir")
def force_prediction() -> JSONResponse:
    """Trigger predictions immediately and return results."""
    run_prediction_and_publish()
    predictions = state_manager.get_full_state().get("prediccion_30min")
    return JSONResponse(
        content={
            "message": "Prediction calculated and published.",
            "prediccion_30min": predictions,
        }
    )


# ------------------------------------------------------------------ #
# Lifecycle Events
# ------------------------------------------------------------------ #


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting up Digital Twin Service | MODE=%s", MODE)

    # 1. Restore historical state if available
    load_snapshot()

    # 2. Start MQTT client (only in non-dev mode)
    if MODE != "DEV_LOCAL":
        try:
            mqtt_client.connect()
        except Exception as e:
            logger.error("Could not connect to Mosquitto broker: %s", e)
    else:
        logger.info("Running in DEV_LOCAL mode — skipping MQTT broker connection.")

    # 3. Schedule periodic loops in the event loop
    loop = asyncio.get_event_loop()

    consolidation_task = loop.create_task(minute_consolidation_loop())
    prediction_task = loop.create_task(prediction_scheduler_loop())
    snapshot_task = loop.create_task(snapshot_scheduler_loop())

    background_tasks.add(consolidation_task)
    background_tasks.add(prediction_task)
    background_tasks.add(snapshot_task)

    # In DEV_LOCAL mode, start the simulation loop
    if MODE == "DEV_LOCAL":
        sim_task = loop.create_task(dev_telemetry_generator())
        background_tasks.add(sim_task)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down Digital Twin Service...")

    # 1. Cancel background loops
    for task in background_tasks:
        task.cancel()

    # 2. Stop MQTT loop
    if MODE != "DEV_LOCAL":
        mqtt_client.disconnect()

    # 3. Save a final snapshot
    logger.info("Saving final state snapshot...")
    save_snapshot()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
