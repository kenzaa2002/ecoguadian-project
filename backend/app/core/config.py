"""
Central configuration – reads from environment variables / .env file
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "EcoGuardian"
    DEBUG: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://ecoguardian:ecoguardian@localhost:5432/ecoguardian1"

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # ── ML ────────────────────────────────────────────────────────────────────
    MODEL_PATH: str = "app/ml/models/smart_home_model.pkl"
    FEATURES_PATH: str = "app/ml/models/smart_home_features.pkl"

    # ── Energy pricing (TND/kWh) ──────────────────────────────────────────────
    ENERGY_PRICE_TND: float = 0.199

    # ── LLM API (Anthropic Claude for chatbot) ────────────────────────────────
    ANTHROPIC_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
