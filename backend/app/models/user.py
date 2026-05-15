"""
ORM model: User
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    username   = Column(String, unique=True, index=True, nullable=False)
    full_name  = Column(String, nullable=True)
    hashed_pw  = Column(String, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    dashboards           = relationship("Dashboard",          back_populates="owner",  cascade="all, delete-orphan")
    predictions          = relationship("Prediction",         back_populates="user",   cascade="all, delete-orphan")
    weekly_consumptions  = relationship("WeeklyConsumption",  back_populates="user",   cascade="all, delete-orphan")
    notifications        = relationship("Notification",       back_populates="user",   cascade="all, delete-orphan")
