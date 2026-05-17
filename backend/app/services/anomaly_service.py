from __future__ import annotations

import csv
import math
import logging
import os
from functools import lru_cache
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Constants 
ROLLING_WINDOW    = 4      # weeks to look back for rolling stats
Z_THRESHOLD_WARN  = 2.0    # |z| > this  →  warning anomaly
Z_THRESHOLD_CRIT  = 3.5    # |z| > this  →  critical anomaly
WARMUP_WEEKS      = 4      # weeks before we switch from baseline to rolling
DATASET_PATH      = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "energy_weekly_anomaly.csv"
)


# Baseline loader (population statistics from the dataset)


@lru_cache(maxsize=1)
def _load_baseline() -> Dict[str, Dict[str, float]]:
  
    baseline: Dict[str, List[float]] = {}

    try:
        path = os.path.abspath(DATASET_PATH)
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hs     = int(row["household_size"])
                kwh    = float(row["weekly_kwh"])
                is_hot = int(row["is_hot_season"])
                is_cold= int(row["is_cold_season"])
                season = "hot" if is_hot else ("cold" if is_cold else "neutral")
                key    = f"{hs}_{season}"
                baseline.setdefault(key, []).append(kwh)

        result: Dict[str, Dict[str, float]] = {}
        for key, vals in baseline.items():
            mean = sum(vals) / len(vals)
            std  = math.sqrt(sum((v - mean)**2 for v in vals) / len(vals))
            result[key] = {"mean": mean, "std": max(std, mean * 0.05), "count": len(vals)}

        logger.info("Anomaly baseline loaded: %d buckets from %s", len(result), path)
        return result

    except FileNotFoundError:
        logger.warning("Baseline CSV not found at %s — will use global fallback", DATASET_PATH)
        return {}
    except Exception as exc:
        logger.warning("Could not load baseline: %s", exc)
        return {}


def _get_baseline_stats(
    household_size: int,
    is_hot_season: int,
    is_cold_season: int,
) -> Optional[Dict[str, float]]:
    """Return baseline stats for the closest household-size bucket."""
    baseline = _load_baseline()
    if not baseline:
        return None

    season = "hot" if is_hot_season else ("cold" if is_cold_season else "neutral")

    # Exact match first
    key = f"{household_size}_{season}"
    if key in baseline:
        return baseline[key]

    # Fall back to nearest household size
    available_sizes = sorted(
        set(int(k.split("_")[0]) for k in baseline),
        key=lambda s: abs(s - household_size)
    )
    if available_sizes:
        best_key = f"{available_sizes[0]}_{season}"
        if best_key in baseline:
            return baseline[best_key]
        # Try any season for that size
        for s in ("neutral", "cold", "hot"):
            fallback = f"{available_sizes[0]}_{s}"
            if fallback in baseline:
                return baseline[fallback]

    return None


# Core detection logic


def _compute_z(value: float, mean: float, std: float) -> float:
    std_safe = max(std, mean * 0.05, 0.1)
    return (value - mean) / std_safe


def _severity(z: float) -> str:
    az = abs(z)
    if az > Z_THRESHOLD_CRIT:
        return "critical"
    if az > Z_THRESHOLD_WARN:
        return "warning"
    return "normal"


def _build_explanation(
    weekly_kwh: float,
    z_score: float,
    rolling_mean: float,
    rolling_std: float,
    anomaly_type: str,
    used_baseline: bool,
    household_size: int,
) -> Dict[str, Any]:
    """Build the human-readable explanation dict stored in anomaly_detail."""
    direction = "higher" if z_score > 0 else "lower"
    pct_diff  = abs((weekly_kwh - rolling_mean) / rolling_mean * 100) if rolling_mean else 0
    severity  = _severity(z_score)

    if anomaly_type == "high":
        headline = f" Unusually HIGH consumption this week (+{pct_diff:.0f}% above normal)"
        tips = [
            "Check if HVAC has been running longer than usual.",
            "Look for appliances left on standby or running overnight.",
            "Compare with last week — did you have more occupants?",
        ]
    elif anomaly_type == "low":
        headline = f" Unusually LOW consumption this week (-{pct_diff:.0f}% below normal)"
        tips = [
            "This could reflect reduced occupancy or appliance off-time.",
            "Verify the reading is correct — a meter error may give low values.",
        ]
    else:
        headline = " Consumption within normal range"
        tips = []

    return {
        "headline":        headline,
        "severity":        severity,
        "direction":       direction if anomaly_type != "none" else "none",
        "weekly_kwh":      round(weekly_kwh, 2),
        "rolling_mean":    round(rolling_mean, 2),
        "rolling_std":     round(rolling_std, 2),
        "z_score":         round(z_score, 3),
        "pct_deviation":   round(pct_diff, 1),
        "used_baseline":   used_baseline,
        "household_size":  household_size,
        "tips":            tips,
    }


def detect_anomaly(
    weekly_kwh: float,
    past_readings: List[float],        
    household_size: int = 1,
    is_hot_season: int  = 0,
    is_cold_season: int = 0,
) -> Dict[str, Any]:
    """
    Main entry point.

    Args:
        weekly_kwh:      This week's total consumption in kWh
        past_readings:   The user's last N weekly readings (oldest first)
        household_size:  Number of people in the household
        is_hot_season:   1 if current week is June-August
        is_cold_season:  1 if current week is Dec-Feb

    Returns:
        {
            "is_anomaly":    bool,
            "anomaly_type":  "none" | "high" | "low",
            "z_score":       float,
            "rolling_mean":  float,
            "rolling_std":   float,
            "severity":      "normal" | "warning" | "critical",
            "used_baseline": bool,
            "detail":        { headline, tips, ... }
        }
    """
    used_baseline = False

    # ── Decide which statistics to use ────────────────────────────────────────
    window = past_readings[-ROLLING_WINDOW:] if past_readings else []

    if len(window) >= WARMUP_WEEKS:
        # ── Rolling user-history stats ─────────────────────────────────────
        rolling_mean = sum(window) / len(window)
        variance     = sum((v - rolling_mean)**2 for v in window) / len(window)
        rolling_std  = max(math.sqrt(variance), rolling_mean * 0.05)
        z_score      = _compute_z(weekly_kwh, rolling_mean, rolling_std)

    else:
        # ── Population baseline (new user or insufficient history) ─────────
        stats = _get_baseline_stats(household_size, is_hot_season, is_cold_season)

        if stats:
            rolling_mean = stats["mean"]
            rolling_std  = stats["std"]
            used_baseline = True
        else:
            # Last resort: use whatever the user has
            if window:
                rolling_mean = sum(window) / len(window)
                rolling_std  = rolling_mean * 0.15
            else:
                # Absolutely no data — cannot detect anomaly yet
                return {
                    "is_anomaly":    False,
                    "anomaly_type":  "none",
                    "z_score":       0.0,
                    "rolling_mean":  weekly_kwh,
                    "rolling_std":   0.0,
                    "severity":      "normal",
                    "used_baseline": False,
                    "detail": {
                        "headline": " Not enough history yet — submit more weeks to enable detection.",
                        "severity": "normal",
                        "tips": [],
                        "used_baseline": False,
                    },
                }

        z_score = _compute_z(weekly_kwh, rolling_mean, rolling_std)

    # ── Classify ──────────────────────────────────────────────────────────────
    is_anomaly   = abs(z_score) > Z_THRESHOLD_WARN
    anomaly_type = ("high" if z_score > 0 else "low") if is_anomaly else "none"
    severity     = _severity(z_score)

    detail = _build_explanation(
        weekly_kwh, z_score, rolling_mean, rolling_std,
        anomaly_type, used_baseline, household_size,
    )

    return {
        "is_anomaly":    is_anomaly,
        "anomaly_type":  anomaly_type,
        "z_score":       round(z_score, 4),
        "rolling_mean":  round(rolling_mean, 3),
        "rolling_std":   round(rolling_std,  3),
        "severity":      severity,
        "used_baseline": used_baseline,
        "detail":        detail,
    }


# ════════════════════════════════════════════════════════════════════════════════
# Notification message builder
# ════════════════════════════════════════════════════════════════════════════════

def build_notification(
    result: Dict[str, Any],
    week_number: int,
    year: int,
    username: str,
) -> Optional[Dict[str, str]]:
    """
    Build a notification payload if the result is an anomaly.
    Returns None when no notification is needed.
    """
    if not result["is_anomaly"]:
        return None

    detail    = result["detail"]
    severity  = result["severity"]
    atype     = result["anomaly_type"]
    pct       = detail.get("pct_deviation", 0)
    mean      = result["rolling_mean"]
    kwh       = detail.get("weekly_kwh", 0)

    if atype == "high":
        title = f" High energy alert — Week {week_number}/{year}"
        message = (
            f"Hi {username}, your consumption this week was {kwh:.1f} kWh — "
            f"{pct:.0f}% above your recent average of {mean:.1f} kWh. "
            f"{detail.get('tips', ['Check your appliances.'])[0]}"
        )
    else:
        title = f" Low energy alert — Week {week_number}/{year}"
        message = (
            f"Hi {username}, your consumption this week was {kwh:.1f} kWh — "
            f"{pct:.0f}% below your recent average of {mean:.1f} kWh. "
            "Please verify your meter reading."
        )

    level = "critical" if severity == "critical" else "warning"

    return {"title": title, "message": message, "level": level}
