"""
EcoGuardian Backend – FastAPI entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import engine, Base
from app.api.routes import (
    auth, users, dashboards, predictions,
    recommendations, chatbot, history, reports,
    weekly, notifications,
)

# ── Create all tables on startup ──────────────────────────────────────────────
# Import all models so Base.metadata knows about every table
import app.models  # noqa: F401
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EcoGuardian API",
    description="AI-powered household energy consumption prediction, anomaly detection & optimisation",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,            prefix="/api/auth",            tags=["Auth"])
app.include_router(users.router,           prefix="/api/users",           tags=["Users"])
app.include_router(dashboards.router,      prefix="/api/dashboards",      tags=["Dashboards"])
app.include_router(predictions.router,     prefix="/api/predictions",     tags=["Predictions"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["Recommendations"])
app.include_router(chatbot.router,         prefix="/api/chatbot",         tags=["Chatbot"])
app.include_router(history.router,         prefix="/api/history",         tags=["History"])
app.include_router(reports.router,         prefix="/api/reports",         tags=["Reports"])
# ── New in v2 ──────────────────────────────────────────────────────────────
app.include_router(weekly.router,          prefix="/api/weekly",          tags=["Weekly Consumption & Anomaly Detection"])
app.include_router(notifications.router,   prefix="/api/notifications",   tags=["Notifications"])


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "app": "EcoGuardian API v2.0"}
