"""
LangChain agent service for EcoBot.
Creates a tool-calling agent backed by Ollama (local LLM) via langchain-ollama.
Tools wrap existing backend services for personalised energy advice.
"""
from __future__ import annotations

import logging
import math
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from langchain_ollama import ChatOllama
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

from app.core.config import settings
from app.models.user import User
from app.models.prediction import Prediction
from app.ml.predictor import _detect_appliance
from app.services.recommendation_service import generate_recommendations

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are **EcoBot**, the official AI chatbot of the EcoGuardian energy management platform in Tunisia.

You are helpful, friendly, concise, and highly practical. Your role is to answer all user questions related to household energy consumption, bills, appliances, anomalies, solar energy, and the EcoGuardian platform.

### Core Knowledge
- Electricity price: 0.199 TND/kWh (STEG)
- Tunisia solar potential: 2,8003,200 sun hours per year
- HVAC typically consumes 4060% of household energy
- Focus on actionable advice tailored to Tunisian households

### Available Tools (Use exact tool names only when needed):

1. **get_user_context**
   Get the user's latest prediction data (avg monthly kWh, peak, main appliance, monthly cost, etc.)

2. **detect_appliance**
   Identify the main energy-consuming appliance from input features

3. **generate_recommendations**
   Call the recommendation engine to get personalized energy saving suggestions

4. **calculate_energy_cost**
   Calculate current bill, potential savings, ROI, or payback period

5. **analyze_anomaly**
   Analyze and explain consumption anomalies or spikes

6. **solar_potential_advisor**
   Give solar panel advice based on user consumption

7. **general_energy_knowledge**
   Retrieve general information about energy efficiency, appliances, weather impact, and best practices

### Behavior Rules
- Be conversational and natural.
- Always try to be helpful and solution-oriented.
- When the user asks for advice, optimization, or "what should I do?", use the **generate_recommendations** tool.
- When the user mentions high bill, spike, or anomaly use relevant analysis tools.
- Always personalize your answer using **get_user_context** when available.
- Keep responses concise (26 sentences maximum when possible).
- Use TND, STEG, and Tunisian context naturally.
- If the user wants detailed recommendations, call the tool and present them clearly (numbered list).

### Response Style
- Friendly and encouraging tone
- Use bullet points or numbered lists for recommendations
- Include estimated savings in TND whenever possible
- End with a relevant follow-up question to keep the conversation going"""


def _build_user_context(db: Session, user: User, dashboard_id: Optional[int]) -> str:
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
        f"avg {latest.avg_monthly_kwh} kWh/month, "
        f"peak {latest.peak_kwh} kWh, "
        f"main appliance: {latest.appliance_label}, "
        f"monthly cost approx {latest.month1_cost:.2f} TND."
    )


def _convert_messages(messages: List[dict]) -> Tuple[str, List[BaseMessage]]:
    if not messages:
        return "", []
    *history, last = messages
    chat_history: List[BaseMessage] = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            chat_history.append(HumanMessage(content=content))
        elif role == "assistant":
            chat_history.append(AIMessage(content=content))
    if last.get("role") == "user":
        return last.get("content", ""), chat_history
    chat_history.append(AIMessage(content=last.get("content", "")))
    return "", chat_history


def create_ecobot_agent(
    db: Session,
    user: User,
    dashboard_id: Optional[int] = None,
) -> AgentExecutor:
    user_context = _build_user_context(db, user, dashboard_id)
    system_prompt = SYSTEM_PROMPT
    if user_context:
        system_prompt += f"\n\n### Current User Context\n{user_context}"

    llm = ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_MODEL,
        temperature=0.3,
        num_predict=512,
    )

    @tool
    def get_user_context() -> str:
        """Get the user's latest prediction data (avg monthly kWh, peak, main appliance, monthly cost, etc.). Use this to personalise your response."""
        return user_context or "No prediction data available yet. Ask the user to run a prediction first."

    @tool
    def detect_appliance(
        household_size: int,
        weather_temperature: float,
        is_hot_season: bool = False,
        is_cold_season: bool = False,
        is_weekend: bool = False,
        hvac: bool = False,
        fridge: bool = False,
        water_heater: bool = False,
        ev_charger: bool = False,
        washing_machine: bool = False,
        dryer: bool = False,
        dishwasher: bool = False,
        oven: bool = False,
        microwave: bool = False,
        tv: bool = False,
        lighting: bool = False,
    ) -> str:
        """Identify the main energy-consuming appliance from input features."""
        features = {
            "Household_Size": household_size,
            "Weather_Temperature": weather_temperature,
            "Is_Hot_Season": int(is_hot_season),
            "Is_Cold_Season": int(is_cold_season),
            "Is_Weekend": int(is_weekend),
            "DayOfWeek": 0,
            "Appliance_Type_HVAC": int(hvac),
            "Appliance_Type_Fridge": int(fridge),
            "Appliance_Type_Water_Heater": int(water_heater),
            "Appliance_Type_Electric_Vehicle_Charger": int(ev_charger),
            "Appliance_Type_Washing_Machine": int(washing_machine),
            "Appliance_Type_Dryer": int(dryer),
            "Appliance_Type_Dishwasher": int(dishwasher),
            "Appliance_Type_Oven": int(oven),
            "Appliance_Type_Microwave": int(microwave),
            "Appliance_Type_TV": int(tv),
            "Appliance_Type_Lighting": int(lighting),
        }
        label, base_kwh = _detect_appliance(features)
        return f"Main appliance identified: {label} (estimated base consumption: {base_kwh} kWh/day)"

    @tool
    def generate_recommendations(
        avg_monthly_kwh: float,
        appliance_label: str = "Unknown",
        temperature: float = 20.0,
        household_size: int = 1,
        is_hot_season: bool = False,
        is_cold_season: bool = False,
        is_weekend: bool = False,
        evening_occupancy: bool = False,
    ) -> str:
        """Get personalised energy saving recommendations based on consumption patterns and appliances."""
        features = {
            "Weather_Temperature": temperature,
            "Household_Size": household_size,
            "Is_Hot_Season": int(is_hot_season),
            "Is_Cold_Season": int(is_cold_season),
            "Is_Weekend": int(is_weekend),
            "Occupancy_Pattern_Evening": int(evening_occupancy),
            "Appliance_Type_HVAC": int(appliance_label == "HVAC"),
            "Appliance_Type_Electric_Vehicle_Charger": int(appliance_label == "EV Charger"),
            "Appliance_Type_Water_Heater": int(appliance_label == "Water Heater"),
        }
        recs = generate_recommendations(features, appliance_label, avg_monthly_kwh)
        if not recs:
            return "No specific recommendations available at this time."
        lines = [f"{i+1}. {r}" for i, r in enumerate(recs)]
        return "Here are your personalised energy saving tips:\n" + "\n".join(lines)

    @tool
    def calculate_energy_cost(
        monthly_kwh: float,
        price_per_kwh: float = 0.199,
    ) -> str:
        """Calculate current energy bill, potential savings, or payback period. Default price is 0.199 TND/kWh (STEG Tunisia)."""
        monthly_cost = monthly_kwh * price_per_kwh
        yearly_cost = monthly_cost * 12
        savings_10 = monthly_cost * 0.10
        savings_20 = monthly_cost * 0.20
        savings_30 = monthly_cost * 0.30

        return (
            f"**Energy Cost Analysis**\n"
            f"- Monthly consumption: {monthly_kwh:.0f} kWh\n"
            f"- Monthly bill: **{monthly_cost:.2f} TND**\n"
            f"- Yearly bill: **{yearly_cost:.2f} TND**\n\n"
            f"**Potential Savings**\n"
            f"- With 10% reduction: save {savings_10:.2f} TND/month ({savings_10*12:.2f} TND/year)\n"
            f"- With 20% reduction: save {savings_20:.2f} TND/month ({savings_20*12:.2f} TND/year)\n"
            f"- With 30% reduction: save {savings_30:.2f} TND/month ({savings_30*12:.2f} TND/year)\n\n"
            f"Tip: LED lighting and HVAC optimization alone can save 1525%!"
        )

    @tool
    def analyze_anomaly(
        weekly_kwh: float,
        rolling_average_kwh: float,
        rolling_std_kwh: float = 0.0,
    ) -> str:
        """Analyze and explain consumption anomalies or spikes compared to normal usage."""
        if rolling_std_kwh <= 0:
            rolling_std_kwh = rolling_average_kwh * 0.15

        z_score = (weekly_kwh - rolling_average_kwh) / max(rolling_std_kwh, 0.1)
        pct_dev = ((weekly_kwh - rolling_average_kwh) / rolling_average_kwh) * 100

        if abs(z_score) > 2:
            direction = "higher" if z_score > 0 else "lower"
            severity = "CRITICAL" if abs(z_score) > 3.5 else "WARNING"
            return (
                f"**Anomaly Detected!** {severity}\n"
                f"- This week: {weekly_kwh:.1f} kWh ({pct_dev:+.1f}% vs normal)\n"
                f"- Normal range: ~{rolling_average_kwh:.1f} kWh/week\n"
                f"- Z-score: {z_score:.2f} ({direction})\n\n"
                f"**Possible causes:**\n"
                f"- Extended HVAC use due to weather\n"
                f"- Extra appliances or guests\n"
                f"- Equipment malfunction\n\n"
                f"**Recommended actions:**\n"
                f"- Check if any appliance was left on\n"
                f"- Review your weekly habits\n"
                f"- Run a new prediction to compare"
            )
        return (
            f"Your consumption of {weekly_kwh:.1f} kWh is within normal range "
            f"(~{rolling_average_kwh:.1f} kWh, {pct_dev:+.1f}% deviation). No anomaly detected."
        )

    @tool
    def solar_potential_advisor(
        avg_monthly_kwh: float,
        roof_area_sqm: float = 50.0,
    ) -> str:
        """Give solar panel advice based on user consumption. Tunisia has 28003200 sun hours/year."""
        yearly_kwh = avg_monthly_kwh * 12
        yearly_cost = yearly_kwh * 0.199

        system_kwp = yearly_kwh / 1600
        system_kwp = max(1, round(system_kwp, 1))

        needed_area = system_kwp * 7
        panels = math.ceil(system_kwp * 1000 / 400)

        system_cost = system_kwp * 2500
        yearly_savings = yearly_kwh * 0.199 * 0.8
        payback_years = system_cost / max(yearly_savings, 1)

        offset_pct = min(80, round(system_kwp * 1600 / yearly_kwh * 100)) if yearly_kwh > 0 else 0

        return (
            f"**Solar Potential Assessment for Tunisia**\n\n"
            f"**Your Profile**\n"
            f"- Annual consumption: {yearly_kwh:.0f} kWh/year\n"
            f"- Current annual cost: {yearly_cost:.2f} TND\n\n"
            f"**Recommended System**\n"
            f"- Size: **{system_kwp} kWp** ({panels} panels, ~{needed_area:.0f} m roof space)\n"
            f"- Est. production: {system_kwp * 1600:.0f} kWh/year\n"
            f"- Bill offset: ~{offset_pct}%\n\n"
            f"**Investment**\n"
            f"- Est. cost: **{system_cost:,.0f} TND**\n"
            f"- Est. yearly savings: **{yearly_savings:,.0f} TND**\n"
            f"- Payback period: **~{payback_years:.1f} years**\n\n"
            f"With Tunisia's excellent solar resources, this system would generate "
            f"clean energy for 25+ years!"
        )

    @tool
    def general_energy_knowledge(query: str) -> str:
        """Retrieve general information about energy efficiency, appliances, weather impact, and best practices."""
        q = query.lower()

        if any(w in q for w in ["hvac", "air condition", "heating", "cooling", "ac"]):
            return (
                "**HVAC Energy Tips**\n"
                "- HVAC uses 4060% of household energy in Tunisia\n"
                "- Set thermostat 2C closer to outdoor temp to save ~10%\n"
                "- Clean filters every 13 months\n"
                "- Use ceiling fans to feel 34C cooler at low cost\n"
                "- Seal gaps around doors/windows to reduce heating load by 15%"
            )
        if any(w in q for w in ["fridge", "refrigerator", "freezer"]):
            return (
                "**Fridge Efficiency Tips**\n"
                "- Keep at 4C (fridge) and -18C (freezer)\n"
                "- Clean condenser coils every 6 months\n"
                "- Check door seals\n"
                "- Keep fridge 3/4 full for optimal efficiency\n"
                "- Save up to 15% with proper maintenance"
            )
        if any(w in q for w in ["led", "lighting", "bulb", "light"]):
            return (
                "**Lighting Efficiency**\n"
                "- LEDs use 75% less energy than incandescent bulbs\n"
                "- LEDs last 1525x longer\n"
                "- Switch all bulbs to LED and save ~10% on your bill\n"
                "- Use motion sensors for outdoor lights\n"
                "- Make use of natural light during the day"
            )
        if any(w in q for w in ["water heater", "chauffe-eau"]):
            return (
                "**Water Heater Tips**\n"
                "- Set thermostat to 55C\n"
                "- Insulate the tank to save up to 16%\n"
                "- Use timer to heat only when needed\n"
                "- Take shorter showers\n"
                "- Consider solar water heater for Tunisia's sunny climate"
            )
        if any(w in q for w in ["ev", "electric vehicle", "charger", "car"]):
            return (
                "**EV Charging Tips**\n"
                "- Charge overnight (11 PM  6 AM) for off-peak benefits\n"
                "- Use scheduled charging via your car's app\n"
                "- Consider solar panels to power your EV for free\n"
                "- Level 2 chargers are 3x faster than standard outlets\n"
                "- An EV uses ~0.2 kWh/km on average"
            )
        if any(w in q for w in ["steg", "tariff", "price", "rate", "bill"]):
            return (
                "**STEG Electricity Pricing**\n"
                "- Current rate: **0.199 TND/kWh**\n"
                "- Average Tunisian home: 250400 kWh/month ~ 5080 TND/month\n"
                "- HVAC optimization can reduce bills by 1525%\n"
                "- Solar panels can offset 6080% of consumption"
            )
        if any(w in q for w in ["tunisia", "tunisian"]):
            return (
                "**Energy in Tunisia**\n"
                "- Solar potential: 2,8003,200 sun hours/year (excellent!)\n"
                "- STEG is the national electricity provider\n"
                "- Electricity rate: 0.199 TND/kWh\n"
                "- Growing adoption of solar panels and smart home tech\n"
                "- HVAC is the biggest energy consumer in Tunisian homes"
            )
        return (
            "I can help with:\n"
            "- Energy consumption analysis and predictions\n"
            "- Appliance efficiency tips\n"
            "- Solar energy potential in Tunisia\n"
            "- Bill calculation and cost optimization\n"
            "- Anomaly and spike detection\n"
            "- HVAC, lighting, water heater, and EV charging tips\n\n"
            "What would you like to know?"
        )

    tools = [
        get_user_context,
        detect_appliance,
        generate_recommendations,
        calculate_energy_cost,
        analyze_anomaly,
        solar_potential_advisor,
        general_energy_knowledge,
    ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=settings.DEBUG,
        max_iterations=5,
        handle_parsing_errors=True,
    )


def run_agent(
    db: Session,
    user: User,
    messages: List[dict],
    dashboard_id: Optional[int] = None,
) -> str:
    try:
        agent_executor = create_ecobot_agent(db, user, dashboard_id)
        input_text, chat_history = _convert_messages(messages)

        if not input_text:
            return "Hello! I'm EcoBot, your energy assistant. How can I help you today?"

        result = agent_executor.invoke({
            "input": input_text,
            "chat_history": chat_history,
        })

        return result.get("output", "I'm sorry, I couldn't generate a response. Please try again.")

    except Exception as exc:
        logger.error("Agent error: %s", exc, exc_info=True)
        return (
            "I'm sorry, I encountered an issue connecting to my AI engine. "
            "Please make sure Ollama is running locally with the model "
            f"'{settings.OLLAMA_MODEL}' available. "
            "In the meantime, try asking about energy tips, appliance advice, or cost calculations!"
        )
