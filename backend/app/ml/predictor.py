"""
ML Service – generates 3-month household energy forecasts.

Updated behavior:
- Supports MULTI-APPLIANCE prediction.
- Each selected appliance is predicted separately.
- Quantities are supported: HVAC x1, Fridge x2, EV Charger x1, etc.
- The total forecast is the sum of all selected appliance forecasts.

The frontend sends appliance fields like:
    Appliance_Type_HVAC = 1
    Appliance_Type_Fridge = 2
    Appliance_Type_Electric_Vehicle_Charger = 1

Values greater than 0 are treated as quantities.
"""
from __future__ import annotations

import math
import logging
from functools import lru_cache
from typing import Dict, Any, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Appliance one-hot/quantity field -> label + base daily kWh fallback value
APPLIANCE_META: Dict[str, Tuple[str, float]] = {
    "Appliance_Type_Dishwasher":               ("Dishwasher",       1.5),
    "Appliance_Type_Dryer":                    ("Dryer",            4.0),
    "Appliance_Type_Electric_Vehicle_Charger": ("EV Charger",      10.0),
    "Appliance_Type_Fridge":                   ("Fridge",           1.2),
    "Appliance_Type_HVAC":                     ("HVAC",             8.0),
    "Appliance_Type_Lighting":                 ("Lighting",         0.8),
    "Appliance_Type_Microwave":                ("Microwave",        0.4),
    "Appliance_Type_Oven":                     ("Oven",             2.0),
    "Appliance_Type_TV":                       ("TV",               0.5),
    "Appliance_Type_Washing_Machine":          ("Washing Machine",  2.5),
    "Appliance_Type_Water_Heater":             ("Water Heater",     3.5),
}

APPLIANCE_LABEL_ENCODING = {
    "Dishwasher": 0,
    "Dryer": 1,
    "EV Charger": 2,
    "Fridge": 3,
    "HVAC": 4,
    "Lighting": 5,
    "Microwave": 6,
    "Oven": 7,
    "TV": 8,
    "Washing Machine": 9,
    "Water Heater": 10,
}

SEASON_ENCODING = {"spring": 0, "summer": 1, "autumn": 2, "winter": 3}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load the pickled model once. Returns (model, feature_list) or (None, None)."""
    try:
        import joblib
        from app.core.config import settings

        model = joblib.load(settings.MODEL_PATH)
        features = joblib.load(settings.FEATURES_PATH)
        logger.info("ML model loaded ✓ features=%d", len(features))
        return model, features
    except Exception as exc:
        logger.warning("Could not load ML model (%s) – using statistical fallback", exc)
        return None, None


def _get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def _selected_appliances(features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract selected appliances from the request.

    Old behavior used only one appliance.
    New behavior keeps every appliance where quantity > 0.
    """
    selected: List[Dict[str, Any]] = []

    for key, (label, base_kwh) in APPLIANCE_META.items():
        raw_value = features.get(key, 0)
        try:
            quantity = int(raw_value or 0)
        except (TypeError, ValueError):
            quantity = 0

        if quantity > 0:
            selected.append({
                "key": key,
                "label": label,
                "quantity": quantity,
                "base_kwh": base_kwh,
            })

    # Safe fallback: keep the prediction usable even if no appliance is selected.
    if not selected:
        selected.append({
            "key": "Appliance_Type_Unknown",
            "label": "Unknown",
            "quantity": 1,
            "base_kwh": 2.0,
        })

    return selected


def _detect_appliance(features: Dict[str, Any]) -> Tuple[str, float]:
    """
    Backward-compatible helper used elsewhere in the project.
    Returns the highest base-consumption selected appliance.
    """
    selected = _selected_appliances(features)
    main = max(selected, key=lambda a: a["base_kwh"] * a["quantity"])
    return main["label"], main["base_kwh"]


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
    """Build a single feature row matching the notebook's feature structure."""
    temp = features["Weather_Temperature"]
    hsize = features["Household_Size"]
    season = _get_season(month)

    return [
        temp,
        hsize,
        SEASON_ENCODING.get(season, 0),
        APPLIANCE_LABEL_ENCODING.get(appliance_label, 0),
        1 if features.get("Is_Weekend", 0) else 0,
        hour,
        day_of_week,
        month,
        math.sin(2 * math.pi * hour / 24),
        math.cos(2 * math.pi * hour / 24),
        math.sin(2 * math.pi * day_of_week / 7),
        math.cos(2 * math.pi * day_of_week / 7),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
        temp ** 2,
        temp * hsize,
        hour * temp,
        prev_consumption,
        prev_consumption,
        rolling_mean,
        rolling_std,
    ]


def _features_for_single_appliance(features: Dict[str, Any], appliance_key: str) -> Dict[str, Any]:
    """
    Convert a multi-appliance payload into a clean one-appliance feature vector.
    The ML model expects one active appliance label at a time.
    """
    single = dict(features)
    for key in APPLIANCE_META.keys():
        single[key] = 1 if key == appliance_key else 0
    return single


def _statistical_fallback(features: Dict[str, Any], appliance_label: str, base_kwh: float) -> float:
    """
    Rule-based DAILY consumption estimate when the ML model file is unavailable.
    """
    household_size = max(float(features.get("Household_Size", 1)), 1.0)
    temp = float(features.get("Weather_Temperature", 20))

    kwh = base_kwh * (0.75 + household_size * 0.15)

    if appliance_label == "HVAC":
        # HVAC depends strongly on temperature gap from comfort temperature.
        kwh += abs(temp - 20) * 0.18 * household_size

    if appliance_label == "Fridge":
        # Fridge runs continuously and increases slightly with heat.
        if temp > 28:
            kwh *= 1.10

    if appliance_label == "Water Heater" and features.get("Is_Cold_Season", 0):
        kwh *= 1.15

    if appliance_label == "EV Charger":
        kwh *= 1.20

    if features.get("Is_Hot_Season", 0) and appliance_label in {"HVAC", "Fridge"}:
        kwh *= 1.15

    if features.get("Is_Cold_Season", 0) and appliance_label in {"HVAC", "Water Heater"}:
        kwh *= 1.20

    if features.get("Is_Weekend", 0):
        kwh *= 1.05

    if features.get("Occupancy_Pattern_Evening", 0) and appliance_label in {"Lighting", "TV", "Oven", "Microwave"}:
        kwh *= 1.10

    return max(kwh, 0.1)


def _predict_single_appliance_months(
    input_features: Dict[str, Any],
    appliance_key: str,
    appliance_label: str,
    base_kwh: float,
    base_month: int,
) -> List[float]:
    """
    Predict 3 monthly kWh values for ONE appliance with quantity = 1.
    Quantity multiplication is applied outside this function.
    """
    model, feature_names = _load_model()
    single_features = _features_for_single_appliance(input_features, appliance_key)
    monthly_kwh: List[float] = []

    for m_offset in range(3):
        month = ((base_month - 1 + m_offset) % 12) + 1
        day_total = 0.0
        prev = base_kwh * 0.1
        rolling_buffer: List[float] = []

        # 30 days × 24 representative hours
        for day in range(30):
            dow = (int(single_features["DayOfWeek"]) + day) % 7
            hourly: List[float] = []

            for hour in range(24):
                r_mean = float(np.mean(rolling_buffer[-24:])) if rolling_buffer else prev
                r_std = float(np.std(rolling_buffer[-24:])) if len(rolling_buffer) > 1 else 0.1

                if model is not None:
                    row = _build_row(
                        single_features,
                        hour,
                        dow,
                        month,
                        appliance_label,
                        prev,
                        r_mean,
                        r_std,
                    )

                    if feature_names and len(row) < len(feature_names):
                        row += [0.0] * (len(feature_names) - len(row))
                    row = row[:len(feature_names)] if feature_names else row

                    pred_val = float(model.predict([row])[0])
                    pred_val = max(pred_val, 0.0)
                else:
                    pred_val = _statistical_fallback(single_features, appliance_label, base_kwh) / 24

                hourly.append(pred_val)
                rolling_buffer.append(pred_val)
                prev = pred_val

            day_total += sum(hourly)

        monthly_kwh.append(round(day_total, 2))

    return monthly_kwh


def predict_three_months(input_features: Dict[str, Any], base_month: int = 1) -> Dict[str, Any]:
    """
    Generate a 3-month forecast.

    If multiple appliances are selected, each appliance is predicted separately,
    then summed into the final household forecast.
    """
    from app.core.config import settings

    selected = _selected_appliances(input_features)
    price = settings.ENERGY_PRICE_TND

    total_monthly = [0.0, 0.0, 0.0]
    appliance_breakdown: List[Dict[str, Any]] = []

    for item in selected:
        label = item["label"]
        key = item["key"]
        quantity = int(item["quantity"])
        base_kwh = float(item["base_kwh"])

        monthly_for_one = _predict_single_appliance_months(
            input_features=input_features,
            appliance_key=key,
            appliance_label=label,
            base_kwh=base_kwh,
            base_month=base_month,
        )

        monthly_for_quantity = [round(v * quantity, 2) for v in monthly_for_one]

        for idx in range(3):
            total_monthly[idx] += monthly_for_quantity[idx]

        forecasts = []
        for i, kwh in enumerate(monthly_for_quantity):
            month_number = ((base_month - 1 + i) % 12) + 1
            forecasts.append({
                "month": i + 1,
                "label": MONTH_NAMES[month_number - 1],
                "kwh": round(kwh, 2),
                "cost_tnd": round(kwh * price, 2),
            })

        appliance_breakdown.append({
            "appliance_label": label,
            "quantity": quantity,
            "forecasts": forecasts,
            "avg_monthly_kwh": round(float(np.mean(monthly_for_quantity)), 2),
            "peak_kwh": round(float(max(monthly_for_quantity)), 2),
            "total_cost_tnd": round(sum(f["cost_tnd"] for f in forecasts), 2),
        })

    total_monthly = [round(v, 2) for v in total_monthly]
    avg_kwh = round(float(np.mean(total_monthly)), 2)
    peak_kwh = round(float(max(total_monthly)), 2)

    forecasts = []
    for i, kwh in enumerate(total_monthly):
        month_number = ((base_month - 1 + i) % 12) + 1
        forecasts.append({
            "month": i + 1,
            "label": MONTH_NAMES[month_number - 1],
            "kwh": round(kwh, 2),
            "cost_tnd": round(kwh * price, 2),
        })

    if len(selected) == 1:
        appliance_label = selected[0]["label"]
    else:
        appliance_label = "Multi-appliance"

    return {
        "forecasts": forecasts,
        "avg_monthly_kwh": avg_kwh,
        "peak_kwh": peak_kwh,
        "total_cost_tnd": round(sum(f["cost_tnd"] for f in forecasts), 2),
        "appliance_label": appliance_label,
        "selected_appliances": [
            {
                "appliance_label": a["label"],
                "quantity": int(a["quantity"]),
            }
            for a in selected
        ],
        "appliance_breakdown": appliance_breakdown,
    }
