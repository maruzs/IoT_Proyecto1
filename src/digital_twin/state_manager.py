import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """Manages the in-memory state of the Digital Twin, including current sensor readings,

    1-hour history (60 records at 1-minute resolution), and active alerts.
    Includes thread safety using a lock because MQTT callback threads and
    FastAPI request threads execute concurrently.
    """

    def __init__(self) -> None:
        self.lock = threading.Lock()

        # Current state of all variables
        self.estado_actual: Dict[str, Any] = {
            "temperatura": None,
            "humedad": None,
            "gas": None,
            "movimiento": False,
            "persona": False,
            "led": False,
            "buzzer": False,
            "sensor_extra": None,
        }

        # 1-hour history containing exactly the last 60 entries at 1-minute resolution
        # Each entry: {"ts": "ISO-8601", "temperatura": float, "humedad": float, "gas": float}
        self.historial_1h: deque = deque(maxlen=60)

        # Active alerts list
        self.alertas_activas: List[str] = []

        # Current predictions (calculated by Linear Regression)
        self.prediccion_30min: Dict[str, Any] = {
            "valores": {
                "temperatura": None,
                "humedad": None,
                "gas": None,
            },
            "metodo": "linear_regression",
            "timestamp_prediccion": None,
        }

        # Temporary buffers to calculate the 1-minute average
        self._temp_samples: List[float] = []
        self._hum_samples: List[float] = []
        self._gas_samples: List[float] = []

    def update_sensor_readings(
        self,
        temp: Optional[float],
        hum: Optional[float],
        gas: Optional[float],
        sensor_extra: Optional[float],
    ) -> None:
        """Update the current state and add readings to the 1-minute averaging buffers."""
        with self.lock:
            if temp is not None:
                self.estado_actual["temperatura"] = temp
                self._temp_samples.append(temp)
            if hum is not None:
                self.estado_actual["humedad"] = hum
                self._hum_samples.append(hum)
            if gas is not None:
                self.estado_actual["gas"] = gas
                self._gas_samples.append(gas)
            if sensor_extra is not None:
                self.estado_actual["sensor_extra"] = sensor_extra

            self._evaluate_thresholds()

    def update_actuator_state(self, key: str, value: bool) -> None:
        """Update status for boolean actuators or state properties like led, buzzer, movimiento, persona."""
        with self.lock:
            if key in self.estado_actual:
                self.estado_actual[key] = value
                logger.debug("Updated actuator state: %s = %s", key, value)
                self._evaluate_thresholds()

    def add_alert(self, alert_name: str) -> None:
        """Manually add an alert to the active alerts list if not present."""
        with self.lock:
            if alert_name not in self.alertas_activas:
                self.alertas_activas.append(alert_name)
                logger.info("Alert added: %s", alert_name)

    def remove_alert(self, alert_name: str) -> None:
        """Manually remove an alert from the active alerts list."""
        with self.lock:
            if alert_name in self.alertas_activas:
                self.alertas_activas.remove(alert_name)
                logger.info("Alert removed: %s", alert_name)

    def _evaluate_thresholds(self) -> None:
        """Evaluate thresholds for active alerts list.

        Umbrales del enunciado:
        - Temperatura > 30 °C -> alerta_temperatura_alta
        - Gas > 400 ppm (o 1020 en el buzzer, use 400 según T-021) -> alerta_gas_alto
        """
        temp = self.estado_actual["temperatura"]
        gas = self.estado_actual["gas"]

        # Temp alert
        if temp is not None and temp > 30.0:
            if "temperatura_alta" not in self.alertas_activas:
                self.alertas_activas.append("temperatura_alta")
        else:
            if "temperatura_alta" in self.alertas_activas:
                self.alertas_activas.remove("temperatura_alta")

        # Gas alert
        if gas is not None and gas > 400.0:
            if "gas_alto" not in self.alertas_activas:
                self.alertas_activas.append("gas_alto")
        else:
            if "gas_alto" in self.alertas_activas:
                self.alertas_activas.remove("gas_alto")

    def consolidate_minute_average(self) -> None:
        """Calculate the average of the last minute's samples and push to the history deque.

        If no samples were received, fall back to current values of estado_actual
        if they exist, to prevent history gaps.
        """
        with self.lock:
            ts = datetime.now(timezone.utc).isoformat()

            # Temp average
            if self._temp_samples:
                avg_temp = sum(self._temp_samples) / len(self._temp_samples)
                self._temp_samples.clear()
            else:
                avg_temp = self.estado_actual["temperatura"]

            # Hum average
            if self._hum_samples:
                avg_hum = sum(self._hum_samples) / len(self._hum_samples)
                self._hum_samples.clear()
            else:
                avg_hum = self.estado_actual["humedad"]

            # Gas average
            if self._gas_samples:
                avg_gas = sum(self._gas_samples) / len(self._gas_samples)
                self._gas_samples.clear()
            else:
                avg_gas = self.estado_actual["gas"]

            # Only append if we have valid numerical readings for the core metrics
            if avg_temp is not None or avg_hum is not None or avg_gas is not None:
                record = {
                    "ts": ts,
                    "temperatura": round(avg_temp, 2) if avg_temp is not None else None,
                    "humedad": round(avg_hum, 2) if avg_hum is not None else None,
                    "gas": round(avg_gas, 2) if avg_gas is not None else None,
                }
                self.historial_1h.append(record)
                logger.info("Consolidated 1-minute history record: %s", record)

    def set_predictions(self, temp_pred: Optional[float], hum_pred: Optional[float], gas_pred: Optional[float]) -> None:
        """Set the predictions computed by the regression module."""
        with self.lock:
            self.prediccion_30min["valores"]["temperatura"] = round(temp_pred, 2) if temp_pred is not None else None
            self.prediccion_30min["valores"]["humedad"] = round(hum_pred, 2) if hum_pred is not None else None
            self.prediccion_30min["valores"]["gas"] = round(gas_pred, 2) if gas_pred is not None else None
            self.prediccion_30min["timestamp_prediccion"] = datetime.now(timezone.utc).isoformat()
            logger.info("Updated 30-minute predictions: %s", self.prediccion_30min["valores"])

    def get_full_state(self) -> Dict[str, Any]:
        """Return a snapshot of the full Digital Twin state."""
        with self.lock:
            return {
                "ultimo_update": datetime.now(timezone.utc).isoformat(),
                "estado_actual": self.estado_actual.copy(),
                "historial_1h": list(self.historial_1h),
                "alertas_activas": list(self.alertas_activas),
                "prediccion_30min": self.prediccion_30min.copy(),
            }

    def import_state(self, state_dict: Dict[str, Any]) -> None:
        """Restore full state from a dict (for snapshot loading)."""
        with self.lock:
            try:
                self.estado_actual = state_dict.get("estado_actual", self.estado_actual)
                self.alertas_activas = state_dict.get("alertas_activas", self.alertas_activas)
                self.prediccion_30min = state_dict.get("prediccion_30min", self.prediccion_30min)

                # Restore deque history
                history_list = state_dict.get("historial_1h", [])
                self.historial_1h.clear()
                for record in history_list:
                    self.historial_1h.append(record)

                logger.info(
                    "State successfully imported from snapshot. History records count: %d",
                    len(self.historial_1h),
                )
            except Exception as e:
                logger.error("Failed to parse snapshot state dict: %s", e)
