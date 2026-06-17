import unittest
from datetime import datetime, timedelta, timezone
from .predictor import parse_iso, predict_variable_linear, predict_all_metrics


class TestPredictor(unittest.TestCase):

    def setUp(self):
        # Create a mock base timestamp
        self.base_time = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)

    def test_parse_iso(self):
        # Test UTC Z format
        dt1 = parse_iso("2026-06-17T12:00:00Z")
        self.assertEqual(dt1.tzinfo, timezone.utc)
        self.assertEqual(dt1.hour, 12)

        # Test offset format
        dt2 = parse_iso("2026-06-17T12:00:00+00:00")
        self.assertEqual(dt2.tzinfo, timezone.utc)

    def test_insufficient_points(self):
        # Test that we return None if we have fewer than min_points
        history = [
            {"ts": (self.base_time + timedelta(minutes=i)).isoformat(), "temperatura": 20.0 + i}
            for i in range(3)
        ]
        pred = predict_variable_linear(history, "temperatura", horizon_minutes=30.0, min_points=5)
        self.assertIsNone(pred)

    def test_perfect_linear_progression(self):
        # Test: y = 2 * x + 10. Readings at 1-minute intervals.
        # Points: (0, 10), (1, 12), (2, 14), (3, 16), (4, 18), (5, 20)
        # Prediction at horizon 30 minutes from last point (x = 5):
        # Target x = 5 + 30 = 35. Expected y = 2 * 35 + 10 = 80.
        history = [
            {
                "ts": (self.base_time + timedelta(minutes=i)).isoformat(),
                "temperatura": float(2 * i + 10),
                "humedad": 50.0,
                "gas": 300.0,
            }
            for i in range(6)
        ]

        # Single variable prediction
        pred_temp = predict_variable_linear(history, "temperatura", horizon_minutes=30.0, min_points=5)
        self.assertIsNotNone(pred_temp)
        self.assertAlmostEqual(pred_temp, 80.0, places=2)

    def test_clip_values(self):
        # Test that humidity predictions are capped at 100.0%
        # Let's create a steep upward slope for humidity: y = 10 * x + 60
        # Readings at x = 0..5 -> y = 60..110
        # Prediction at horizon 30 (x = 35) -> expected 410 -> capped at 100.0
        history = [
            {
                "ts": (self.base_time + timedelta(minutes=i)).isoformat(),
                "temperatura": 25.0,
                "humedad": float(10 * i + 60),
                "gas": 100.0,
            }
            for i in range(6)
        ]

        pred_hum = predict_variable_linear(history, "humedad", horizon_minutes=30.0, min_points=5)
        self.assertEqual(pred_hum, 100.0)

        # Test that gas is capped at >= 0.0 (steep negative slope)
        # y = -100 * x + 300
        # x = 0..5 -> y = 300, 200, 100, 0, -100, -200
        # x = 35 -> expected -3200 -> capped at 0.0
        history_gas = [
            {
                "ts": (self.base_time + timedelta(minutes=i)).isoformat(),
                "temperatura": 25.0,
                "humedad": 50.0,
                "gas": float(-100 * i + 300),
            }
            for i in range(6)
        ]
        pred_gas = predict_variable_linear(history_gas, "gas", horizon_minutes=30.0, min_points=5)
        self.assertEqual(pred_gas, 0.0)

    def test_predict_all_metrics(self):
        history = [
            {
                "ts": (self.base_time + timedelta(minutes=i)).isoformat(),
                "temperatura": float(25.0 + i * 0.1),
                "humedad": float(50.0 - i * 0.2),
                "gas": float(200.0 + i * 5),
            }
            for i in range(6)
        ]
        # x = 0..5 (last x = 5)
        # temp: y = 0.1 * x + 25. At x = 35: 0.1 * 35 + 25 = 28.5
        # hum: y = -0.2 * x + 50. At x = 35: -0.2 * 35 + 50 = 43.0
        # gas: y = 5 * x + 200. At x = 35: 5 * 35 + 200 = 375.0
        temp_pred, hum_pred, gas_pred = predict_all_metrics(history, horizon_minutes=30.0, min_points=5)
        self.assertAlmostEqual(temp_pred, 28.5, places=2)
        self.assertAlmostEqual(hum_pred, 43.0, places=2)
        self.assertAlmostEqual(gas_pred, 375.0, places=2)


if __name__ == "__main__":
    unittest.main()
