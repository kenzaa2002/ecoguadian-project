from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import all models for Base.metadata (nécessaire pour create_all)
import app.models  # noqa: F401

from app.db.database import engine, Base
from app.api.routes.auth import router as auth_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.chatbot import router as chatbot_router
from app.api.routes.users import router as users_router
from app.api.routes.dashboards import router as dashboards_router
from app.api.routes.history import router as history_router
from app.api.routes.weekly import router as weekly_router
from app.api.routes.notifications import router as notifications_router  # ← AJOUT

# Créer toutes les tables au démarrage
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EcoGuardian API",
    description="AI-Powered Smart Home Energy Prediction Platform",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router,          prefix="/api/auth",          tags=["Auth"])
app.include_router(predictions_router,   prefix="/api/predictions",   tags=["Predictions"])
app.include_router(chatbot_router,       prefix="/api/chatbot",       tags=["Chatbot"])
app.include_router(users_router,         prefix="/api/users",         tags=["Users"])
app.include_router(dashboards_router,    prefix="/api/dashboards",    tags=["Dashboards"])
app.include_router(history_router,       prefix="/api/history",       tags=["History"])
app.include_router(weekly_router,        prefix="/api/weekly",        tags=["Weekly"])        # ← CORRIGÉ
app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"]) # ← AJOUT

@app.get("/")
async def root():
    return {"message": "🚀 EcoGuardian API v2.0 is running!", "docs": "/docs"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)