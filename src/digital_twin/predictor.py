import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


def parse_iso(ts_str: str) -> datetime:
    """Parse an ISO-8601 string, safely handling trailing 'Z' for UTC."""
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)


def predict_variable_linear(
    history: List[Dict[str, Any]],
    key: str,
    horizon_minutes: float = 30.0,
    min_points: int = 5,
) -> Optional[float]:
    """Perform a linear regression (numpy.polyfit of degree 1) on the specified sensor key

    and project its value `horizon_minutes` into the future from the last point.

    Args:
        history: List of historical records.
        key: The key of the metric to predict (e.g. "temperatura", "humedad", "gas").
        horizon_minutes: Prediction horizon relative to the last point (default 30 min).
        min_points: Minimum number of valid points required to compute a regression.

    Returns:
        The predicted float value, or None if computation is not possible.
    """
    # 1. Filter out records that don't have the key or where the value is None
    valid_records = []
    for r in history:
        if "ts" in r and r.get(key) is not None:
            valid_records.append(r)

    if len(valid_records) < min_points:
        logger.warning(
            "Insufficient data points for '%s' prediction. Have %d, need at least %d.",
            key,
            len(valid_records),
            min_points,
        )
        return None

    # 2. Extract timestamps and values
    try:
        times = [parse_iso(r["ts"]) for r in valid_records]
        values = [float(r[key]) for r in valid_records]
    except Exception as e:
        logger.error("Error parsing history records for '%s': %s", key, e)
        return None

    # 3. Convert timestamps to relative minutes from the first record
    first_time = times[0]
    x_values = [(t - first_time).total_seconds() / 60.0 for t in times]
    y_values = values

    # 4. Fit linear regression: y = m * x + c
    try:
        # np.polyfit(x, y, 1) returns [slope, intercept]
        m, c = np.polyfit(x_values, y_values, 1)
        logger.debug("Regression for '%s': slope=%f, intercept=%f", key, m, c)
    except Exception as e:
        logger.error("Regression fit failed for '%s': %s", key, e)
        return None

    # 5. Predict value at horizon relative to the last record
    last_x = x_values[-1]
    pred_x = last_x + horizon_minutes
    pred_y = m * pred_x + c

    # Clip values to physically realistic boundaries
    if key == "temperatura":
        # Keep within reasonable home limits
        pred_y = max(-10.0, min(100.0, pred_y))
    elif key == "humedad":
        # Humidity is a percentage 0-100%
        pred_y = max(0.0, min(100.0, pred_y))
    elif key == "gas":
        # Gas ppm is non-negative
        pred_y = max(0.0, pred_y)

    return pred_y


def predict_all_metrics(
    history: List[Dict[str, Any]],
    horizon_minutes: float = 30.0,
    min_points: int = 5,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Compute predictions for all continuous variables: temperatura, humedad, and gas.

    Returns:
        A tuple of (temp_pred, hum_pred, gas_pred)
    """
    temp_pred = predict_variable_linear(history, "temperatura", horizon_minutes, min_points)
    hum_pred = predict_variable_linear(history, "humedad", horizon_minutes, min_points)
    gas_pred = predict_variable_linear(history, "gas", horizon_minutes, min_points)

    return temp_pred, hum_pred, gas_pred
