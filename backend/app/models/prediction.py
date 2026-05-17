"""
ORM model: Prediction – stores one prediction run (3-month forecast)
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"),      nullable=False)
    dashboard_id   = Column(Integer, ForeignKey("dashboards.id"), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    # raw inputs stored as JSON for auditability
    input_features = Column(JSON, nullable=False)

    # outputs
    month1_kwh     = Column(Float, nullable=False)
    month2_kwh     = Column(Float, nullable=False)
    month3_kwh     = Column(Float, nullable=False)
    month1_cost    = Column(Float, nullable=False)
    month2_cost    = Column(Float, nullable=False)
    month3_cost    = Column(Float, nullable=False)

    # derived analytics stored for fast re-display
    avg_monthly_kwh  = Column(Float)
    peak_kwh         = Column(Float)
    appliance_label  = Column(String)

    user      = relationship("User",      back_populates="predictions")
    dashboard = relationship("Dashboard", back_populates="predictions")
