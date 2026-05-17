"""
Pydantic v2 schemas – request/response validation
Includes all original schemas + new weekly consumption & notification schemas.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ════════════════════════════════════════════════════════════════════════════════
# AUTH / USER
# ════════════════════════════════════════════════════════════════════════════════
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ════════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
class DashboardCreate(BaseModel):
    name: str
    address: Optional[str] = None
    household_size: int = 1


class DashboardOut(BaseModel):
    id: int
    name: str
    address: Optional[str]
    household_size: int
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════════════════
# PREDICTION
# ════════════════════════════════════════════════════════════════════════════════
class PredictionInput(BaseModel):
    """All fields the user fills in the prediction form."""
    dashboard_id: Optional[int] = None

    Household_Size: int
    Weather_Temperature: float
    DayOfWeek: int
    Is_Weekend: int
    Is_Cold_Season: int
    Is_Hot_Season: int
    Appliance_Type_Dishwasher: int = 0
    Appliance_Type_Dryer: int = 0
    Appliance_Type_Electric_Vehicle_Charger: int = 0
    Appliance_Type_Fridge: int = 0
    Appliance_Type_HVAC: int = 0
    Appliance_Type_Lighting: int = 0
    Appliance_Type_Microwave: int = 0
    Appliance_Type_Oven: int = 0
    Appliance_Type_TV: int = 0
    Appliance_Type_Washing_Machine: int = 0
    Appliance_Type_Water_Heater: int = 0
    Occupancy_Pattern_Evening: int = 0
    Occupancy_Pattern_Mixed: int = 0

    @field_validator("DayOfWeek")
    @classmethod
    def validate_day(cls, v):
        if not 0 <= v <= 6:
            raise ValueError("DayOfWeek must be 0–6")
        return v


class MonthForecast(BaseModel):
    month: int
    label: str
    kwh: float
    cost_tnd: float


class ApplianceForecastBreakdown(BaseModel):
    appliance_label: str
    quantity: int
    forecasts: List[MonthForecast]
    avg_monthly_kwh: float
    peak_kwh: float
    total_cost_tnd: float


class SelectedApplianceOut(BaseModel):
    appliance_label: str
    quantity: int


class PredictionOut(BaseModel):
    id: Optional[int]
    input_features: Dict[str, Any]
    forecasts: List[MonthForecast]
    avg_monthly_kwh: float
    peak_kwh: float
    total_cost_tnd: float
    appliance_label: str
    selected_appliances: List[SelectedApplianceOut] = []
    appliance_breakdown: List[ApplianceForecastBreakdown] = []
    recommendations: List[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════════════════
# WEEKLY CONSUMPTION  (new feature)
# ════════════════════════════════════════════════════════════════════════════════

class WeeklyConsumptionCreate(BaseModel):
    """
    What the user manually submits each week.
    week_number = ISO week (0-52).  If omitted, the current week is used.
    """
    dashboard_id:    Optional[int]   = None
    week_number:     Optional[int]   = None   # 0-52; auto-derived if None
    year:            Optional[int]   = None   # auto-derived if None
    weekly_kwh:      float                    # total kWh consumed this week
    avg_temperature: Optional[float] = None   # °C – optional context
    is_hot_season:   int             = 0
    is_cold_season:  int             = 0
    is_hvac_week:    int             = 0
    household_size:  int             = 1

    @field_validator("weekly_kwh")
    @classmethod
    def kwh_positive(cls, v):
        if v <= 0:
            raise ValueError("weekly_kwh must be positive")
        return round(v, 3)

    @field_validator("week_number")
    @classmethod
    def valid_week(cls, v):
        if v is not None and not (0 <= v <= 52):
            raise ValueError("week_number must be 0–52")
        return v


class AnomalyDetail(BaseModel):
    headline:      str
    severity:      str
    direction:     str
    weekly_kwh:    float
    rolling_mean:  float
    rolling_std:   float
    z_score:       float
    pct_deviation: float
    used_baseline: bool
    tips:          List[str]

    class Config:
        from_attributes = True


class WeeklyConsumptionOut(BaseModel):
    id:               int
    dashboard_id:     Optional[int]
    week_number:      int
    year:             int
    weekly_kwh:       float
    avg_temperature:  Optional[float]
    is_hot_season:    int
    is_cold_season:   int
    is_hvac_week:     int
    household_size:   int
    # ── anomaly results ─────────────────────────────────
    is_anomaly:       bool
    anomaly_type:     str     # "none" | "high" | "low"
    z_score:          float
    rolling_mean:     Optional[float]
    rolling_std:      Optional[float]
    anomaly_detail:   Optional[Dict[str, Any]]
    # ── notification ────────────────────────────────────
    notification_sent: bool
    created_at:        datetime

    class Config:
        from_attributes = True


class WeeklyConsumptionList(BaseModel):
    items:      List[WeeklyConsumptionOut]
    total:      int
    anomalies:  int


# ════════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS  (new feature)
# ════════════════════════════════════════════════════════════════════════════════

class NotificationOut(BaseModel):
    id:                    int
    title:                 str
    message:               str
    level:                 str   # "info" | "warning" | "critical"
    category:              str
    is_read:               bool
    read_at:               Optional[datetime]
    extra_data:            Optional[Dict[str, Any]]
    weekly_consumption_id: Optional[int]
    created_at:            datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    items:       List[NotificationOut]
    total:       int
    unread:      int


# ════════════════════════════════════════════════════════════════════════════════
# CHATBOT
# ════════════════════════════════════════════════════════════════════════════════
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    dashboard_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str


# ════════════════════════════════════════════════════════════════════════════════
# HISTORY
# ════════════════════════════════════════════════════════════════════════════════
class PredictionHistoryItem(BaseModel):
    id:              int
    dashboard_id:    Optional[int]
    dashboard_name:  Optional[str]
    appliance_label: str
    avg_monthly_kwh: float
    peak_kwh:        float
    month1_kwh:      float
    month1_cost:     float
    created_at:      datetime

    class Config:
        from_attributes = True
