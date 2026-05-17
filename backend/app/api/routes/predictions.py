from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.models.dashboard import Dashboard
from app.schemas.schemas import (
    PredictionInput,
    PredictionOut,
    MonthForecast,
    ApplianceForecastBreakdown,
    SelectedApplianceOut,
)
from app.ml.predictor import predict_three_months
from app.services.recommendation_service import generate_recommendations

router = APIRouter()


def _to_month_forecasts(forecasts):
    return [MonthForecast(**f) for f in forecasts]


def _to_selected_appliances(items):
    return [SelectedApplianceOut(**item) for item in items or []]


def _to_appliance_breakdown(items):
    breakdown = []
    for item in items or []:
        breakdown.append(
            ApplianceForecastBreakdown(
                appliance_label=item["appliance_label"],
                quantity=item["quantity"],
                forecasts=_to_month_forecasts(item["forecasts"]),
                avg_monthly_kwh=item["avg_monthly_kwh"],
                peak_kwh=item["peak_kwh"],
                total_cost_tnd=item["total_cost_tnd"],
            )
        )
    return breakdown


@router.post("", response_model=PredictionOut, status_code=201)
def run_prediction(
    payload: PredictionInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dash = None
    if payload.dashboard_id:
        dash = (
            db.query(Dashboard)
            .filter(
                Dashboard.id == payload.dashboard_id,
                Dashboard.owner_id == current_user.id,
            )
            .first()
        )
        if not dash:
            raise HTTPException(status_code=404, detail="Dashboard not found")

    features = payload.model_dump(exclude={"dashboard_id"})

    # If a saved house is selected, the household size should come from the
    # database instead of the manual form. This avoids double entry and keeps
    # the prediction consistent with the registered house profile.
    if dash:
        features["Household_Size"] = dash.household_size
    base_month = datetime.utcnow().month

    result = predict_three_months(features, base_month=base_month)
    forecasts = result["forecasts"]

    recs = generate_recommendations(
        features,
        result["appliance_label"],
        result["avg_monthly_kwh"],
    )

    record = Prediction(
        user_id=current_user.id,
        dashboard_id=payload.dashboard_id,
        input_features=features,
        month1_kwh=forecasts[0]["kwh"],
        month2_kwh=forecasts[1]["kwh"],
        month3_kwh=forecasts[2]["kwh"],
        month1_cost=forecasts[0]["cost_tnd"],
        month2_cost=forecasts[1]["cost_tnd"],
        month3_cost=forecasts[2]["cost_tnd"],
        avg_monthly_kwh=result["avg_monthly_kwh"],
        peak_kwh=result["peak_kwh"],
        appliance_label=result["appliance_label"],
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return PredictionOut(
        id=record.id,
        input_features=features,
        forecasts=_to_month_forecasts(forecasts),
        avg_monthly_kwh=result["avg_monthly_kwh"],
        peak_kwh=result["peak_kwh"],
        total_cost_tnd=result["total_cost_tnd"],
        appliance_label=result["appliance_label"],
        selected_appliances=_to_selected_appliances(result.get("selected_appliances", [])),
        appliance_breakdown=_to_appliance_breakdown(result.get("appliance_breakdown", [])),
        recommendations=recs,
        created_at=record.created_at,
    )


@router.get("/{prediction_id}", response_model=PredictionOut)
def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = (
        db.query(Prediction)
        .filter(
            Prediction.id == prediction_id,
            Prediction.user_id == current_user.id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Rebuild the detailed appliance breakdown from the stored input features.
    # This avoids adding a new DB column/migration.
    base_month = record.created_at.month if record.created_at else datetime.utcnow().month
    result = predict_three_months(record.input_features, base_month=base_month)

    recs = generate_recommendations(
        record.input_features,
        result["appliance_label"],
        result["avg_monthly_kwh"],
    )

    return PredictionOut(
        id=record.id,
        input_features=record.input_features,
        forecasts=_to_month_forecasts(result["forecasts"]),
        avg_monthly_kwh=result["avg_monthly_kwh"],
        peak_kwh=result["peak_kwh"],
        total_cost_tnd=result["total_cost_tnd"],
        appliance_label=result["appliance_label"],
        selected_appliances=_to_selected_appliances(result.get("selected_appliances", [])),
        appliance_breakdown=_to_appliance_breakdown(result.get("appliance_breakdown", [])),
        recommendations=recs,
        created_at=record.created_at,
    )
