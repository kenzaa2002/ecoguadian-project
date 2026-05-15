from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.schemas import PredictionHistoryItem

router = APIRouter()

@router.get("", response_model=List[PredictionHistoryItem])
def get_history(
    dashboard_id: Optional[int] = Query(None),
    from_date: Optional[date]   = Query(None),
    to_date:   Optional[date]   = Query(None),
    skip: int  = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (db.query(Prediction)
        .options(joinedload(Prediction.dashboard))
        .filter(Prediction.user_id == current_user.id))
    if dashboard_id: query = query.filter(Prediction.dashboard_id == dashboard_id)
    if from_date:    query = query.filter(Prediction.created_at >= from_date)
    if to_date:      query = query.filter(Prediction.created_at <= to_date)
    records = query.order_by(Prediction.created_at.desc()).offset(skip).limit(limit).all()
    return [PredictionHistoryItem(
        id=r.id, dashboard_id=r.dashboard_id,
        dashboard_name=r.dashboard.name if r.dashboard else None,
        appliance_label=r.appliance_label or "Unknown",
        avg_monthly_kwh=r.avg_monthly_kwh or 0.0, peak_kwh=r.peak_kwh or 0.0,
        month1_kwh=r.month1_kwh, month1_cost=r.month1_cost, created_at=r.created_at,
    ) for r in records]

@router.delete("/{prediction_id}", status_code=204)
def delete_prediction(prediction_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(Prediction).filter(Prediction.id == prediction_id, Prediction.user_id == current_user.id).first()
    if not record: raise HTTPException(status_code=404, detail="Prediction not found")
    db.delete(record); db.commit()
