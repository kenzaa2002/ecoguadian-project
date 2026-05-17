"""
EcoBot agent service.

This version uses Ollama directly instead of LangChain tool-calling agents.
Why?
- Ollama + llama3.1 may return raw tool-call JSON.
- The frontend was displaying this JSON directly.
- This service now returns natural language answers only.

It still uses:
- user prediction context
- recommendation service
- appliance detection
- bill calculation
- solar advice
"""

from __future__ import annotations

import json
import logging
import math
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, SystemMessage

from app.core.config import settings
from app.models.user import User
from app.models.prediction import Prediction
from app.ml.predictor import _detect_appliance
from app.services.recommendation_service import generate_recommendations as recommendation_engine

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are EcoBot, the official AI chatbot of the EcoGuardian energy management platform in Tunisia.

You are helpful, friendly, concise, and practical.
Your role is to answer questions about:
- household energy consumption
- electricity bills
- appliances
- anomalies and energy spikes
- solar energy
- energy saving recommendations
- EcoGuardian platform features

Important context:
- Electricity price in Tunisia: 0.199 TND/kWh
- STEG is the Tunisian electricity provider
- Tunisia has strong solar potential: about 2,800 to 3,200 sun hours per year
- HVAC can consume around 40% to 60% of household energy
- Give advice adapted to Tunisian households when possible

VERY IMPORTANT RESPONSE RULES:
- Never return JSON.
- Never return tool calls.
- Never return function names.
- Never output structures like {"name": "...", "parameters": {...}}.
- Always answer directly in natural language.
- Use clear bullet points when giving recommendations.
- Keep your answer practical and easy to understand.
- Mention estimated savings in TND when useful.
"""


def _build_user_context(db: Session, user: User, dashboard_id: Optional[int]) -> str:
    """
    Build a short context string from the user's latest prediction.
    """
    if not dashboard_id:
        return ""

    latest = (
        db.query(Prediction)
        .filter(
            Prediction.user_id == user.id,
            Prediction.dashboard_id == dashboard_id,
        )
        .order_by(Prediction.created_at.desc())
        .first()
    )

    if not latest:
        return ""

    return (
        f"User context: "
        f"average monthly consumption = {latest.avg_monthly_kwh} kWh/month, "
        f"peak consumption = {latest.peak_kwh} kWh, "
        f"main appliance = {latest.appliance_label}, "
        f"estimated monthly cost = {latest.month1_cost:.2f} TND."
    )


def _convert_messages(messages: List[dict]) -> Tuple[str, List[BaseMessage]]:
    """
    Convert frontend messages to LangChain messages.
    Returns:
    - latest user input
    - previous chat history
    """
    if not messages:
        return "", []

    *history, last = messages
    chat_history: List[BaseMessage] = []

    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if not content:
            continue

        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_history.append(AIMessage(content=content))

    if last.get("role") == "user":
        return last.get("content", ""), chat_history

    if last.get("content"):
        chat_history.append(AIMessage(content=last.get("content", "")))

    return "", chat_history


def _looks_like_json_tool_call(text: str) -> bool:
    """
    Detect raw JSON tool-call outputs returned by the model.
    """
    if not text:
        return False

    cleaned = text.strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return True

    suspicious_patterns = [
        '"name"',
        '"parameters"',
        "generate_recommendations",
        "calculate_energy_cost",
        "solar_potential_advisor",
        "detect_appliance",
        "tool_call",
    ]

    return any(pattern in cleaned for pattern in suspicious_patterns)


def _repair_json_response(text: str, original_question: str) -> str:
    """
    Convert raw JSON/tool-call output into a natural response.
    This is a safety net in case the model still returns JSON.
    """
    question = original_question.lower()

    try:
        data = json.loads(text)
        tool_name = data.get("name", "")
        params = data.get("parameters", {})

        if tool_name == "generate_recommendations":
            appliance = params.get("appliance_label", "your main appliance")
            avg_kwh = float(params.get("avg_monthly_kwh", 300))
            monthly_cost = avg_kwh * 0.199

            return (
                f"To reduce your {appliance} bill, start with the highest-impact actions:\n\n"
                f"1. Adjust your thermostat by 1–2°C to reduce heating or cooling load.\n"
                f"2. Clean or replace HVAC filters regularly to improve airflow.\n"
                f"3. Avoid running heating or cooling when the house is empty.\n"
                f"4. Seal air leaks around windows and doors.\n"
                f"5. Use curtains, ventilation, and natural shading to reduce temperature changes.\n\n"
                f"With an estimated consumption of {avg_kwh:.0f} kWh/month, your bill is around "
                f"{monthly_cost:.2f} TND/month. A 15–20% reduction could save about "
                f"{monthly_cost * 0.15:.2f} to {monthly_cost * 0.20:.2f} TND per month."
            )

    except Exception:
        pass

    if "hvac" in question or "heating" in question or "cooling" in question:
        return (
            "To reduce your HVAC bill, you can:\n\n"
            "1. Set the thermostat closer to the outdoor temperature by 1–2°C.\n"
            "2. Clean or replace filters every 1–3 months.\n"
            "3. Close doors and windows when heating or cooling is active.\n"
            "4. Seal air leaks around windows and doors.\n"
            "5. Avoid using HVAC when nobody is home.\n"
            "6. Use fans, curtains, and natural ventilation when possible.\n\n"
            "Since HVAC is usually one of the biggest energy consumers, these actions can noticeably reduce your STEG bill."
        )

    return (
        "Here is a practical energy-saving answer:\n\n"
        "1. Identify the appliance consuming the most energy.\n"
        "2. Reduce unnecessary usage during peak periods.\n"
        "3. Maintain appliances regularly.\n"
        "4. Use efficient settings and avoid standby consumption.\n"
        "5. Track your monthly kWh to compare improvements.\n\n"
        "A 10–20% reduction in consumption can already create visible savings on your STEG bill."
    )


def _calculate_energy_cost(monthly_kwh: float, price_per_kwh: float = 0.199) -> str:
    """
    Calculate electricity bill and possible savings.
    """
    monthly_cost = monthly_kwh * price_per_kwh
    yearly_cost = monthly_cost * 12

    return (
        f"Energy cost analysis:\n\n"
        f"- Monthly consumption: {monthly_kwh:.0f} kWh\n"
        f"- STEG price used: {price_per_kwh:.3f} TND/kWh\n"
        f"- Estimated monthly bill: {monthly_cost:.2f} TND\n"
        f"- Estimated yearly bill: {yearly_cost:.2f} TND\n\n"
        f"Possible savings:\n"
        f"- 10% reduction: {monthly_cost * 0.10:.2f} TND/month\n"
        f"- 20% reduction: {monthly_cost * 0.20:.2f} TND/month\n"
        f"- 30% reduction: {monthly_cost * 0.30:.2f} TND/month"
    )


def _solar_advice(avg_monthly_kwh: float, roof_area_sqm: float = 50.0) -> str:
    """
    Give simple solar advice for Tunisia.
    """
    yearly_kwh = avg_monthly_kwh * 12
    yearly_cost = yearly_kwh * 0.199

    system_kwp = max(1, round(yearly_kwh / 1600, 1))
    panels = math.ceil(system_kwp * 1000 / 400)
    needed_area = system_kwp * 7

    system_cost = system_kwp * 2500
    yearly_savings = yearly_cost * 0.8
    payback_years = system_cost / max(yearly_savings, 1)

    return (
        f"Solar potential assessment for Tunisia:\n\n"
        f"- Annual consumption: {yearly_kwh:.0f} kWh/year\n"
        f"- Current estimated annual bill: {yearly_cost:.2f} TND\n"
        f"- Recommended solar system: about {system_kwp} kWp\n"
        f"- Estimated number of panels: {panels} panels of 400 W\n"
        f"- Required roof area: about {needed_area:.0f} m²\n"
        f"- Estimated investment: around {system_cost:,.0f} TND\n"
        f"- Estimated yearly savings: around {yearly_savings:,.0f} TND\n"
        f"- Estimated payback period: about {payback_years:.1f} years\n\n"
        f"Tunisia has excellent solar potential, so solar panels can be a strong long-term investment."
    )


def _general_energy_answer(question: str, user_context: str = "") -> Optional[str]:
    """
    Return deterministic answers for common energy questions.
    This avoids unnecessary LLM/tool confusion.
    """
    q = question.lower()

    if "hvac" in q or "air condition" in q or "heating" in q or "cooling" in q or "clim" in q:
        return (
            "To reduce your HVAC bill, focus on these actions:\n\n"
            "1. Adjust the thermostat by 1–2°C. Small changes can reduce consumption significantly.\n"
            "2. Clean or replace HVAC filters every 1–3 months.\n"
            "3. Close windows and doors while heating or cooling.\n"
            "4. Seal air leaks around windows, doors, and poorly insulated areas.\n"
            "5. Avoid running HVAC when the house is empty.\n"
            "6. Use curtains, shading, and natural ventilation to reduce heat gain.\n"
            "7. Schedule regular maintenance to keep the system efficient.\n\n"
            "In many homes, HVAC is the biggest energy consumer, so these changes can reduce your STEG bill noticeably."
        )

    if "bill" in q or "cost" in q or "steg" in q or "price" in q:
        monthly_kwh = 300

        if user_context:
            import re
            match = re.search(r"average monthly consumption = ([0-9.]+)", user_context)
            if match:
                monthly_kwh = float(match.group(1))

        return _calculate_energy_cost(monthly_kwh)

    if "solar" in q or "panel" in q or "photovoltaic" in q:
        monthly_kwh = 300

        if user_context:
            import re
            match = re.search(r"average monthly consumption = ([0-9.]+)", user_context)
            if match:
                monthly_kwh = float(match.group(1))

        return _solar_advice(monthly_kwh)

    if "fridge" in q or "refrigerator" in q or "freezer" in q:
        return (
            "To reduce fridge consumption:\n\n"
            "1. Set the fridge to about 4°C and the freezer to about -18°C.\n"
            "2. Avoid opening the door too often.\n"
            "3. Check the door seals.\n"
            "4. Clean condenser coils every few months.\n"
            "5. Do not place hot food directly inside the fridge.\n\n"
            "A well-maintained fridge can save around 10–15% of its energy use."
        )

    if "lighting" in q or "led" in q or "light" in q:
        return (
            "To reduce lighting consumption:\n\n"
            "1. Replace old bulbs with LED bulbs.\n"
            "2. Turn off lights in empty rooms.\n"
            "3. Use natural daylight whenever possible.\n"
            "4. Use motion sensors for outdoor or hallway lighting.\n\n"
            "LED bulbs can use up to 75% less energy than traditional bulbs."
        )

    if "water heater" in q or "chauffe" in q:
        return (
            "To reduce water heater consumption:\n\n"
            "1. Set the temperature around 55°C.\n"
            "2. Use a timer so it heats water only when needed.\n"
            "3. Insulate the tank and hot water pipes.\n"
            "4. Take shorter showers.\n"
            "5. Consider a solar water heater in Tunisia because of the strong solar potential."
        )

    return None


def run_agent(
    db: Session,
    user: User,
    messages: List[dict],
    dashboard_id: Optional[int] = None,
) -> str:
    """
    Main function called by the chatbot route.
    Always returns a natural language response.
    """
    try:
        input_text, chat_history = _convert_messages(messages)

        if not input_text:
            return "Hello! I'm EcoBot, your energy assistant. How can I help you today?"

        user_context = _build_user_context(db, user, dashboard_id)

        deterministic_answer = _general_energy_answer(input_text, user_context)
        if deterministic_answer:
            return deterministic_answer

        full_system_prompt = SYSTEM_PROMPT

        if user_context:
            full_system_prompt += f"\n\nCurrent user context:\n{user_context}"

        full_system_prompt += (
            "\n\nAnswer the user's latest question naturally. "
            "Do not use JSON. Do not call tools. Do not expose internal functions."
        )

        llm = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=0.3,
            num_predict=512,
        )

        conversation = [SystemMessage(content=full_system_prompt)]
        conversation.extend(chat_history[-6:])
        conversation.append(HumanMessage(content=input_text))

        response = llm.invoke(conversation)

        output = getattr(response, "content", str(response)).strip()

        if _looks_like_json_tool_call(output):
            return _repair_json_response(output, input_text)

        if not output:
            return (
                "I can help you with energy saving, appliance efficiency, bill estimation, "
                "solar potential, or anomaly analysis. What would you like to optimize?"
            )

        return output

    except Exception as exc:
        logger.error("EcoBot error: %s", exc, exc_info=True)

        return (
            "I'm sorry, I encountered an issue connecting to my AI engine. "
            "Please make sure Ollama is running locally with the model "
            f"'{settings.OLLAMA_MODEL}' available. "
            "You can also test it with: ollama run "
            f"{settings.OLLAMA_MODEL}"
        )