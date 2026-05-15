from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard
from app.schemas.schemas import DashboardCreate, DashboardOut

router = APIRouter()

@router.post("", response_model=DashboardOut, status_code=201)
def create_dashboard(payload: DashboardCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dash = Dashboard(owner_id=current_user.id, name=payload.name, address=payload.address, household_size=payload.household_size)
    db.add(dash); db.commit(); db.refresh(dash)
    return dash

@router.get("", response_model=List[DashboardOut])
def list_dashboards(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Dashboard).filter(Dashboard.owner_id == current_user.id).all()

@router.get("/{dashboard_id}", response_model=DashboardOut)
def get_dashboard(dashboard_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dash = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current_user.id).first()
    if not dash: raise HTTPException(status_code=404, detail="Dashboard not found")
    return dash

@router.delete("/{dashboard_id}", status_code=204)
def delete_dashboard(dashboard_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dash = db.query(Dashboard).filter(Dashboard.id == dashboard_id, Dashboard.owner_id == current_user.id).first()
    if not dash: raise HTTPException(status_code=404, detail="Dashboard not found")
    db.delete(dash); db.commit()
