from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.models.dashboard import Dashboard
from app.schemas.schemas import PredictionInput, PredictionOut, MonthForecast
from app.ml.predictor import predict_three_months
from app.services.recommendation_service import generate_recommendations

router = APIRouter()

@router.post("", response_model=PredictionOut, status_code=201)
def run_prediction(payload: PredictionInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.dashboard_id:
        dash = db.query(Dashboard).filter(Dashboard.id == payload.dashboard_id, Dashboard.owner_id == current_user.id).first()
        if not dash: raise HTTPException(status_code=404, detail="Dashboard not found")
    features = payload.model_dump(exclude={"dashboard_id"})
    base_month = datetime.utcnow().month
    result = predict_three_months(features, base_month=base_month)
    recs   = generate_recommendations(features, result["appliance_label"], result["avg_monthly_kwh"])
    forecasts = result["forecasts"]
    record = Prediction(
        user_id=current_user.id, dashboard_id=payload.dashboard_id,
        input_features=features,
        month1_kwh=forecasts[0]["kwh"], month2_kwh=forecasts[1]["kwh"], month3_kwh=forecasts[2]["kwh"],
        month1_cost=forecasts[0]["cost_tnd"], month2_cost=forecasts[1]["cost_tnd"], month3_cost=forecasts[2]["cost_tnd"],
        avg_monthly_kwh=result["avg_monthly_kwh"], peak_kwh=result["peak_kwh"], appliance_label=result["appliance_label"],
    )
    db.add(record); db.commit(); db.refresh(record)
    return PredictionOut(id=record.id, input_features=features, forecasts=[MonthForecast(**f) for f in forecasts],
        avg_monthly_kwh=result["avg_monthly_kwh"], peak_kwh=result["peak_kwh"],
        total_cost_tnd=result["total_cost_tnd"], appliance_label=result["appliance_label"],
        recommendations=recs, created_at=record.created_at)

@router.get("/{prediction_id}", response_model=PredictionOut)
def get_prediction(prediction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(Prediction).filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id).first()
    if not record: raise HTTPException(status_code=404, detail="Prediction not found")
    forecasts = [MonthForecast(month=i+1, label=f"Month {i+1}", kwh=kwh, cost_tnd=cost)
        for i,(kwh,cost) in enumerate([(record.month1_kwh,record.month1_cost),(record.month2_kwh,record.month2_cost),(record.month3_kwh,record.month3_cost)])]
    recs = generate_recommendations(record.input_features, record.appliance_label, record.avg_monthly_kwh)
    from app.core.config import settings
    return PredictionOut(id=record.id, input_features=record.input_features, forecasts=forecasts,
        avg_monthly_kwh=record.avg_monthly_kwh, peak_kwh=record.peak_kwh,
        total_cost_tnd=round(record.month1_cost+record.month2_cost+record.month3_cost,2),
        appliance_label=record.appliance_label, recommendations=recs, created_at=record.created_at)
