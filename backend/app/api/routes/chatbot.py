from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.schemas import ChatRequest, ChatResponse

router = APIRouter()

SYSTEM_PROMPT = """You are EcoBot, an expert AI assistant for the EcoGuardian energy management platform.
You help users understand household energy consumption, weather impact on bills, cost optimisation (prices in TND, rate: 0.199 TND/kWh),
appliance efficiency, solar potential in Tunisia, and smart home automation.
Be concise, practical, and friendly. Only answer questions related to energy, environment, or the EcoGuardian platform."""

def _rule_based_fallback(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["hvac","air condition","heating","cooling"]):
        return "HVAC systems typically account for 40–60% of household energy use. Setting your thermostat 2°C closer to the outdoor temperature can cut costs by ~10%. Regular filter cleaning every 1–3 months also improves efficiency."
    if any(w in m for w in ["solar","panel","photovoltaic"]):
        return "Tunisia receives 2,800–3,200 sun hours/year — excellent for solar. A 3 kWp rooftop system produces 4,500–5,500 kWh/year and can offset 60–80% of an average household's consumption."
    if any(w in m for w in ["cost","bill","price","tnd"]):
        return "At 0.199 TND/kWh, a home using 300 kWh/month pays ~59.7 TND. Switching to LED lighting and optimising HVAC schedules can reduce bills by 15–25%."
    if any(w in m for w in ["fridge","refrigerator"]):
        return "Fridges run 24/7 making them one of the biggest draws. Keep condenser coils clean, maintain 4°C inside, and ensure door seals are tight to save up to 15%."
    if any(w in m for w in ["anomaly","unusual","spike","high consumption"]):
        return "An anomaly means your weekly consumption deviated more than 2 standard deviations from your recent average. Check for appliances left on, extra occupants, or extreme weather as likely causes."
    return "I can help with energy consumption, appliance efficiency, weather impact on bills, and cost optimisation. What would you like to know?"

@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    context_snippet = ""
    if payload.dashboard_id:
        latest = db.query(Prediction).filter(
            Prediction.user_id == current_user.id,
            Prediction.dashboard_id == payload.dashboard_id,
        ).order_by(Prediction.created_at.desc()).first()
        if latest:
            context_snippet = (f"\n\nUser context: latest prediction shows avg {latest.avg_monthly_kwh} kWh/month, "
                f"peak {latest.peak_kwh} kWh, appliance: {latest.appliance_label}, "
                f"monthly cost ≈ {latest.month1_cost:.2f} TND.")

    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            messages = [{"role": m.role, "content": m.content} for m in payload.messages]
            response = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=512,
                system=SYSTEM_PROMPT + context_snippet, messages=messages,
            )
            return ChatResponse(reply=response.content[0].text)
        except Exception as exc:
            import logging; logging.getLogger(__name__).warning("Anthropic API error: %s", exc)

    last_user_msg = next((m.content for m in reversed(payload.messages) if m.role == "user"), "")
    return ChatResponse(reply=_rule_based_fallback(last_user_msg))
