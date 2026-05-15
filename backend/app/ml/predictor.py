"""
ML Service – loads the trained model and generates monthly energy forecasts.

The notebook trained an ensemble (RF + GB + XGB) on these features:
  'Outdoor Temperature (°C)', 'Household Size', 'season_encoded',
  'Appliance_Type_Label', 'weekday',
  'hour', 'day_of_week', 'month',
  'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos',
  'temp_squared', 'temp_household_interaction', 'hour_temp_interaction',
  'consumption_lag_1h', 'consumption_lag_24h',
  'rolling_mean_24h', 'rolling_std_24h',

The user form feeds a simpler set of features. We map them and simulate
30 daily rows per month (one per day, sweeping hours 0-23) to get a
realistic monthly total.
"""
from __future__ import annotations
import os
import math
import logging
from functools import lru_cache
from typing import Dict, Any, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Appliance one-hot → label + base daily kWh for a rough scaling factor
APPLIANCE_META: Dict[str, Tuple[str, float]] = {
    "Appliance_Type_Dishwasher":                ("Dishwasher",              1.5),
    "Appliance_Type_Dryer":                     ("Dryer",                   4.0),
    "Appliance_Type_Electric_Vehicle_Charger":  ("EV Charger",             10.0),
    "Appliance_Type_Fridge":                    ("Fridge",                  1.2),
    "Appliance_Type_HVAC":                      ("HVAC",                    8.0),
    "Appliance_Type_Lighting":                  ("Lighting",                0.8),
    "Appliance_Type_Microwave":                 ("Microwave",               0.4),
    "Appliance_Type_Oven":                      ("Oven",                    2.0),
    "Appliance_Type_TV":                        ("TV",                      0.5),
    "Appliance_Type_Washing_Machine":           ("Washing Machine",         2.5),
    "Appliance_Type_Water_Heater":              ("Water Heater",            3.5),
}

APPLIANCE_LABEL_ENCODING = {
    "Dishwasher": 0, "Dryer": 1, "EV Charger": 2,
    "Fridge": 3,     "HVAC": 4,  "Lighting": 5,
    "Microwave": 6,  "Oven": 7,  "TV": 8,
    "Washing Machine": 9, "Water Heater": 10,
}

SEASON_ENCODING = {"spring": 0, "summer": 1, "autumn": 2, "winter": 3}


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load the pickled model once. Returns (model, feature_list) or None."""
    try:
        import joblib
        from app.core.config import settings
        model    = joblib.load(settings.MODEL_PATH)
        features = joblib.load(settings.FEATURES_PATH)
        logger.info("ML model loaded ✓  features=%d", len(features))
        return model, features
    except Exception as exc:
        logger.warning("Could not load ML model (%s) – using statistical fallback", exc)
        return None, None


def _get_season(month: int) -> str:
    if month in (12, 1, 2):   return "winter"
    if month in (3, 4, 5):    return "spring"
    if month in (6, 7, 8):    return "summer"
    return "autumn"


def _detect_appliance(features: Dict[str, Any]) -> Tuple[str, float]:
    for key, (label, base_kwh) in APPLIANCE_META.items():
        if features.get(key, 0) == 1:
            return label, base_kwh
    return "Unknown", 2.0


def _build_row(
    features: Dict[str, Any],
    hour: int,
    day_of_week: int,
    month: int,
    appliance_label: str,
    prev_consumption: float,
    rolling_mean: float,
    rolling_std: float,
) -> List[float]:
    """Build a single feature row matching the notebook's FEATURE_COLS."""
    temp  = features["Weather_Temperature"]
    hsize = features["Household_Size"]
    season = _get_season(month)

    return [
        temp,                                   # Outdoor Temperature (°C)
        hsize,                                  # Household Size
        SEASON_ENCODING.get(season, 0),         # season_encoded
        APPLIANCE_LABEL_ENCODING.get(appliance_label, 0),  # Appliance_Type_Label
        1 if features.get("Is_Weekend", 0) else 0,         # weekday (0=weekday,1=weekend)
        hour,                                   # hour
        day_of_week,                            # day_of_week
        month,                                  # month
        math.sin(2 * math.pi * hour / 24),      # hour_sin
        math.cos(2 * math.pi * hour / 24),      # hour_cos
        math.sin(2 * math.pi * day_of_week / 7),# day_sin
        math.cos(2 * math.pi * day_of_week / 7),# day_cos
        math.sin(2 * math.pi * month / 12),     # month_sin
        math.cos(2 * math.pi * month / 12),     # month_cos
        temp ** 2,                              # temp_squared
        temp * hsize,                           # temp_household_interaction
        hour * temp,                            # hour_temp_interaction
        prev_consumption,                       # consumption_lag_1h
        prev_consumption,                       # consumption_lag_24h (approx)
        rolling_mean,                           # rolling_mean_24h
        rolling_std,                            # rolling_std_24h
    ]


def _statistical_fallback(features: Dict[str, Any], appliance_label: str, base_kwh: float) -> float:
    """
    Rule-based daily consumption estimate when the model file is unavailable.
    Returns estimated daily kWh.
    """
    kwh = base_kwh * features["Household_Size"] * 0.6
    temp = features["Weather_Temperature"]
    if features.get("Is_HVAC", 0) or appliance_label == "HVAC":
        kwh += abs(temp - 20) * 0.05 * features["Household_Size"]
    if features.get("Is_Hot_Season", 0):
        kwh *= 1.15
    if features.get("Is_Cold_Season", 0):
        kwh *= 1.20
    return max(kwh, 0.1)


def predict_three_months(
    input_features: Dict[str, Any],
    base_month: int = 1,
) -> Dict[str, Any]:
    """
    Generate a 3-month energy consumption forecast.

    Args:
        input_features: validated dict from PredictionInput
        base_month: calendar month to start from (1-12)

    Returns:
        dict with month forecasts, averages, recommendations
    """
    from app.core.config import settings

    appliance_label, base_kwh = _detect_appliance(input_features)
    model, feature_names = _load_model()

    monthly_kwh: List[float] = []

    for m_offset in range(3):
        month = ((base_month - 1 + m_offset) % 12) + 1
        day_total = 0.0
        prev = base_kwh * 0.1
        rolling_buffer: List[float] = []

        # Simulate 30 days × representative hours to get monthly total
        for day in range(30):
            dow = (input_features["DayOfWeek"] + day) % 7
            hourly = []

            for hour in range(24):
                r_mean = float(np.mean(rolling_buffer[-24:])) if rolling_buffer else prev
                r_std  = float(np.std(rolling_buffer[-24:]))  if len(rolling_buffer) > 1 else 0.1

                if model is not None:
                    row = _build_row(
                        input_features, hour, dow, month,
                        appliance_label, prev, r_mean, r_std
                    )
                    # Pad / trim to match saved feature list length
                    if feature_names and len(row) < len(feature_names):
                        row += [0.0] * (len(feature_names) - len(row))
                    row = row[:len(feature_names)] if feature_names else row

                    pred_val = float(model.predict([row])[0])
                    pred_val = max(pred_val, 0.0)
                else:
                    pred_val = _statistical_fallback(input_features, appliance_label, base_kwh) / 24

                hourly.append(pred_val)
                rolling_buffer.append(pred_val)
                prev = pred_val

            day_total += sum(hourly)

        monthly_kwh.append(round(day_total, 2))

    # ── Compute summary stats ──────────────────────────────────────────────────
    avg_kwh  = round(float(np.mean(monthly_kwh)), 2)
    peak_kwh = round(float(max(monthly_kwh)), 2)
    price    = settings.ENERGY_PRICE_TND

    forecasts = []
    for i, kwh in enumerate(monthly_kwh):
        month_label = ((base_month - 1 + i) % 12) + 1
        MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        forecasts.append({
            "month": i + 1,
            "label": MONTH_NAMES[month_label - 1],
            "kwh":   kwh,
            "cost_tnd": round(kwh * price, 2),
        })

    return {
        "forecasts":        forecasts,
        "avg_monthly_kwh":  avg_kwh,
        "peak_kwh":         peak_kwh,
        "total_cost_tnd":   round(sum(f["cost_tnd"] for f in forecasts), 2),
        "appliance_label":  appliance_label,
    }
