"""
ORM model: Dashboard (one per house)
"""
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Dashboard(Base):
    __tablename__ = "dashboards"

    id             = Column(Integer, primary_key=True, index=True)
    owner_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    name           = Column(String,  nullable=False)
    address        = Column(String,  nullable=True)
    household_size = Column(Integer, default=1)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    owner               = relationship("User",              back_populates="dashboards")
    predictions         = relationship("Prediction",        back_populates="dashboard", cascade="all, delete-orphan")
    weekly_consumptions = relationship("WeeklyConsumption", back_populates="dashboard", cascade="all, delete-orphan")
