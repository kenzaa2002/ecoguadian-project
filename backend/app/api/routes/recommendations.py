from typing import List
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.schemas import PredictionInput
from app.services.recommendation_service import generate_recommendations
from app.ml.predictor import _detect_appliance
from pydantic import BaseModel

router = APIRouter()

class RecommendationRequest(BaseModel):
    features: PredictionInput
    avg_monthly_kwh: float = 150.0

class RecommendationResponse(BaseModel):
    recommendations: List[str]

@router.post("/", response_model=RecommendationResponse)
def get_recommendations(payload: RecommendationRequest, current_user: User = Depends(get_current_user)):
    features = payload.features.model_dump(exclude={"dashboard_id"})
    appliance_label, _ = _detect_appliance(features)
    recs = generate_recommendations(features, appliance_label, payload.avg_monthly_kwh)
    return RecommendationResponse(recommendations=recs)
