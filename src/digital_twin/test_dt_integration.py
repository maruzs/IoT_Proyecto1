import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from .main import state_manager, run_prediction_and_publish, get_state, mqtt_client, SNAPSHOT_PATH
from .predictor import predict_all_metrics, parse_iso


class TestDigitalTwinIntegration(unittest.TestCase):

    def setUp(self):
        # Create a mock base timestamp
        self.base_time = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
        
        # Clear state manager queues & dicts
        state_manager.historial_1h.clear()
        state_manager.alertas_activas.clear()
        state_manager.estado_actual = {
            "temperatura": None,
            "humedad": None,
            "gas": None,
            "movimiento": False,
            "persona": False,
            "led": False,
            "buzzer": False,
            "sensor_extra": None
        }
        
        # Mock MQTT publisher to avoid connection errors during test
        self.original_publish = mqtt_client.publish_prediction
        mqtt_client.publish_prediction = MagicMock()

    def tearDown(self):
        mqtt_client.publish_prediction = self.original_publish

    def test_sensor_ingestion_and_consolidation(self):
        # Ingest a series of readings
        state_manager.update_sensor_readings(temp=25.0, hum=50.0, gas=300.0, sensor_extra=10.0)
        state_manager.update_sensor_readings(temp=26.0, hum=52.0, gas=310.0, sensor_extra=12.0)
        
        # Check current state matches last update
        self.assertEqual(state_manager.estado_actual["temperatura"], 26.0)
        self.assertEqual(state_manager.estado_actual["humedad"], 52.0)
        self.assertEqual(state_manager.estado_actual["gas"], 310.0)

        # Consolidate average
        state_manager.consolidate_minute_average()
        
        # History should have 1 consolidated record
        self.assertEqual(len(state_manager.historial_1h), 1)
        record = state_manager.historial_1h[0]
        # Average temperature: (25.0 + 26.0) / 2 = 25.5
        self.assertAlmostEqual(record["temperatura"], 25.5)
        # Average humidity: (50.0 + 52.0) / 2 = 51.0
        self.assertAlmostEqual(record["humedad"], 51.0)
        # Average gas: (300 + 310) / 2 = 305.0
        self.assertAlmostEqual(record["gas"], 305.0)

    def test_linear_regression_predictions(self):
        # Populate history with linear progression: y = 2x + 10 for temp, y = -1x + 80 for hum, y = 5x + 100 for gas
        for i in range(6):
            state_manager.update_sensor_readings(
                temp=float(2 * i + 10),
                hum=float(-1 * i + 80),
                gas=float(5 * i + 100),
                sensor_extra=42.0
            )
            state_manager.consolidate_minute_average()
            # Manually space timestamps to 1 minute apart
            state_manager.historial_1h[-1]["ts"] = (self.base_time + timedelta(minutes=i)).isoformat()

        # Run predictions
        run_prediction_and_publish()

        res = get_state()
        predictions = res["prediccion_30min"]["valores"]

        # Expected at x = 5 + 30 = 35:
        # Temp: 2 * 35 + 10 = 80
        # Hum: -1 * 35 + 80 = 45
        # Gas: 5 * 35 + 100 = 275
        self.assertAlmostEqual(predictions["temperatura"], 80.0, places=1)
        self.assertAlmostEqual(predictions["humedad"], 45.0, places=1)
        self.assertAlmostEqual(predictions["gas"], 275.0, places=1)

        # Confirm MQTT publish calls were triggered
        self.assertEqual(mqtt_client.publish_prediction.call_count, 3)

    def test_alert_thresholds(self):
        # 1. Normal readings
        state_manager.update_sensor_readings(temp=24.0, hum=50.0, gas=200.0, sensor_extra=10.0)
        self.assertEqual(state_manager.alertas_activas, [])

        # 2. Temperature high (>30C)
        state_manager.update_sensor_readings(temp=31.0, hum=50.0, gas=200.0, sensor_extra=10.0)
        self.assertIn("temperatura_alta", state_manager.alertas_activas)

        # 3. Gas high (>400ppm)
        state_manager.update_sensor_readings(temp=24.0, hum=50.0, gas=450.0, sensor_extra=10.0)
        self.assertIn("gas_alto", state_manager.alertas_activas)
        # Temp alert should be cleared
        self.assertNotIn("temperatura_alta", state_manager.alertas_activas)

    def test_snapshot_persistence(self):
        # Setup temporary path for snapshot
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        global SNAPSHOT_PATH
        original_snapshot_path = SNAPSHOT_PATH
        # Access through modules/variables
        import src.digital_twin.main
        src.digital_twin.main.SNAPSHOT_PATH = tmp_path

        try:
            # 1. Setup mock state
            state_manager.update_sensor_readings(temp=25.0, hum=50.0, gas=300.0, sensor_extra=10.0)
            state_manager.consolidate_minute_average()
            state_manager.historial_1h[-1]["ts"] = self.base_time.isoformat()
            state_manager.add_alert("test_alert")

            # 2. Save snapshot
            src.digital_twin.main.save_snapshot()
            self.assertTrue(os.path.exists(tmp_path))

            # 3. Clear manager
            state_manager.historial_1h.clear()
            state_manager.alertas_activas.clear()
            state_manager.estado_actual["temperatura"] = None

            # 4. Load snapshot
            src.digital_twin.main.load_snapshot()

            # 5. Verify restored state
            self.assertEqual(state_manager.estado_actual["temperatura"], 25.0)
            self.assertIn("test_alert", state_manager.alertas_activas)
            self.assertEqual(len(state_manager.historial_1h), 1)
            self.assertEqual(state_manager.historial_1h[0]["ts"], self.base_time.isoformat())

        finally:
            # Restore path and cleanup
            src.digital_twin.main.SNAPSHOT_PATH = original_snapshot_path
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
