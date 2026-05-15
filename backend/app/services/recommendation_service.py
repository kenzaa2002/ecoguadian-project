from __future__ import annotations
from typing import List, Dict, Any


def generate_recommendations(
    features: Dict[str, Any],
    appliance_label: str,
    avg_monthly_kwh: float,
) -> List[str]:
    """
    Return a prioritised list of personalised recommendations.
    """
    recs: List[str] = []
    temp  = features.get("Weather_Temperature", 20)
    hsize = features.get("Household_Size", 1)
    is_hot  = features.get("Is_Hot_Season", 0)
    is_cold = features.get("Is_Cold_Season", 0)
    is_weekend = features.get("Is_Weekend", 0)
    ev_pattern = features.get("Occupancy_Pattern_Evening", 0)

    # ── HVAC-specific ────────────────────────────────────────────────────────
    if appliance_label == "HVAC" or features.get("Appliance_Type_HVAC", 0):
        recs.append("🌡️ Set your HVAC thermostat 2°C higher in summer and 2°C lower in winter "
                    "to cut energy use by up to 10%.")
        if temp > 30:
            recs.append("☀️ Use ceiling fans alongside AC – they can make rooms feel 3–4°C cooler "
                        "at a fraction of the cost.")
        if temp < 10:
            recs.append("🧥 Seal gaps around doors and windows to reduce heating load by up to 15%.")
        recs.append("⏰ Schedule your HVAC to run 30 minutes before you arrive home rather than "
                    "all day to avoid unnecessary runtime.")

    # ── EV Charger ───────────────────────────────────────────────────────────
    if appliance_label == "EV Charger" or features.get("Appliance_Type_Electric_Vehicle_Charger", 0):
        recs.append("🔋 Charge your EV overnight (11 PM – 6 AM) to benefit from off-peak tariffs "
                    "and reduce grid stress.")
        recs.append("📱 Use your car's app to schedule charging when solar or wind energy is most "
                    "abundant in your region.")

    # ── Water Heater ─────────────────────────────────────────────────────────
    if appliance_label == "Water Heater" or features.get("Appliance_Type_Water_Heater", 0):
        recs.append("🚿 Lower your water heater setpoint to 55°C – it is hot enough and reduces "
                    "standby heat losses significantly.")
        recs.append("🔧 Insulate your water heater tank to save up to 16% on water-heating energy.")

    # ── High average consumption ─────────────────────────────────────────────
    if avg_monthly_kwh > 300:
        recs.append("⚠️ Your predicted monthly consumption exceeds 300 kWh. Consider an energy "
                    "audit to identify the biggest savings opportunities.")
    if avg_monthly_kwh > 200:
        recs.append("💡 Switch to LED bulbs in all rooms – they use 75% less energy than "
                    "traditional incandescent bulbs.")

    # ── Household size ───────────────────────────────────────────────────────
    if hsize >= 4:
        recs.append("🏠 With a large household, smart power strips can eliminate standby power "
                    "draw from entertainment systems, saving ~10% on electronics bills.")

    # ── Seasonal ─────────────────────────────────────────────────────────────
    if is_hot:
        recs.append("🌞 Close blinds on south- and west-facing windows during peak afternoon sun "
                    "to naturally reduce cooling demand.")
    if is_cold:
        recs.append("❄️ Use a programmable thermostat to lower heat at night and when away – "
                    "each degree reduction saves ~3% on heating costs.")

    # ── Weekend / occupancy ──────────────────────────────────────────────────
    if is_weekend:
        recs.append("🏡 On weekends with high occupancy, run heavy appliances (dishwasher, washer) "
                    "in full loads only to maximise efficiency per cycle.")
    if ev_pattern:
        recs.append("🌙 Evening occupancy peaks coincide with high grid demand. Shift dishwasher "
                    "and dryer cycles to after 9 PM when possible.")

    # ── General always-on tips ───────────────────────────────────────────────
    recs.append("📊 Install a smart meter or plug-level monitor to track real-time consumption "
                "and identify phantom loads.")
    recs.append("♻️ Consider solar panels – a 3 kWp system can offset 3,000–4,500 kWh/year "
                "in Tunisia's sunny climate.")

    # Return top 6 most relevant
    return recs[:6]
