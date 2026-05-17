"""
ORM model: WeeklyConsumption
Stores one manually-entered weekly reading per user/dashboard.
Anomaly detection is run at insertion time and the result is stored here.
"""
from sqlalchemy import (
    Column, Integer, Float, String, Boolean,
    ForeignKey, DateTime, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class WeeklyConsumption(Base):
    __tablename__ = "weekly_consumptions"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"),      nullable=False)
    dashboard_id   = Column(Integer, ForeignKey("dashboards.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # ── What the user submitted ───────────────────────────────────────────────
    week_number    = Column(Integer, nullable=False)   # ISO week 0-52
    year           = Column(Integer, nullable=False)
    weekly_kwh     = Column(Float,   nullable=False)   # total kWh this week
    avg_temperature= Column(Float,   nullable=True)    # optional context
    is_hot_season  = Column(Integer, default=0)
    is_cold_season = Column(Integer, default=0)
    is_hvac_week   = Column(Integer, default=0)
    household_size = Column(Integer, default=1)

    # ── Anomaly detection results ─────────────────────────────────────────────
    is_anomaly     = Column(Boolean, default=False)
    anomaly_type   = Column(String,  default="none")   # "none" | "high" | "low"
    z_score        = Column(Float,   default=0.0)
    rolling_mean   = Column(Float,   nullable=True)
    rolling_std    = Column(Float,   nullable=True)
    anomaly_detail = Column(JSON,    nullable=True)    # rich explanation dict

    # ── Notification ──────────────────────────────────────────────────────────
    notification_sent = Column(Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    user      = relationship("User",      back_populates="weekly_consumptions")
    dashboard = relationship("Dashboard", back_populates="weekly_consumptions")
