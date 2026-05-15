"""
ORM model: Notification
Stores all in-app notifications. Can be extended to email/push later.
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    # ── Content ───────────────────────────────────────────────────────────────
    title        = Column(String,  nullable=False)
    message      = Column(String,  nullable=False)
    level        = Column(String,  default="info")     # "info" | "warning" | "critical"
    category     = Column(String,  default="anomaly")  # "anomaly" | "system"
    extra_data   = Column(JSON,    nullable=True)       # arbitrary payload

    # ── Read state ────────────────────────────────────────────────────────────
    is_read      = Column(Boolean, default=False)
    read_at      = Column(DateTime(timezone=True), nullable=True)

    # ── Link back to the consumption record that triggered it ─────────────────
    weekly_consumption_id = Column(Integer, ForeignKey("weekly_consumptions.id"), nullable=True)

    user = relationship("User", back_populates="notifications")
