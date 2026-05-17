"""
Weekly Consumption routes
=========================
POST /api/weekly/           — submit a new weekly reading
GET  /api/weekly/           — list user's history (paginated)
GET  /api/weekly/{id}       — fetch a single record
GET  /api/weekly/stats/      — summary stats (avg, anomaly rate)
DELETE /api/weekly/{id}     — delete a record
"""
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.dashboard import Dashboard
from app.models.weekly_consumption import WeeklyConsumption
from app.models.notification import Notification
from app.schemas.schemas import (
    WeeklyConsumptionCreate,
    WeeklyConsumptionOut,
    WeeklyConsumptionList,
)
from app.services.anomaly_service import detect_anomaly, build_notification

router = APIRouter()


def _current_week_year():
    now = datetime.now(timezone.utc)
    return int(now.strftime("%W")), now.year


# ── POST – submit a new weekly reading ────────────────────────────────────────
@router.post("", response_model=WeeklyConsumptionOut, status_code=201)
def submit_weekly(
    payload: WeeklyConsumptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve optional week/year from payload or current date
    week_number = payload.week_number
    year        = payload.year
    if week_number is None or year is None:
        w, y = _current_week_year()
        week_number = week_number if week_number is not None else w
        year        = year        if year        is not None else y

    # Validate dashboard ownership
    dash = None
    if payload.dashboard_id:
        dash = db.query(Dashboard).filter(
            Dashboard.id == payload.dashboard_id,
            Dashboard.owner_id == current_user.id,
        ).first()
        if not dash:
            raise HTTPException(status_code=404, detail="Dashboard not found")

    # If a saved house is selected, use its stored household size instead of
    # asking the user to enter the same information again.
    household_size = dash.household_size if dash else payload.household_size

    # Prevent duplicate submission for the same week
    existing = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.user_id      == current_user.id,
        WeeklyConsumption.week_number  == week_number,
        WeeklyConsumption.year         == year,
        WeeklyConsumption.dashboard_id == payload.dashboard_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A reading for week {week_number}/{year} already exists (id={existing.id}). "
                   "Delete it first or use a different week_number.",
        )

    # Fetch past readings (last 8 weeks, same dashboard) for rolling stats
    past_records: List[WeeklyConsumption] = (
        db.query(WeeklyConsumption)
        .filter(
            WeeklyConsumption.user_id      == current_user.id,
            WeeklyConsumption.dashboard_id == payload.dashboard_id,
        )
        .order_by(WeeklyConsumption.year.asc(), WeeklyConsumption.week_number.asc())
        .limit(8)
        .all()
    )
    past_kwh = [r.weekly_kwh for r in past_records]

    # ── Run anomaly detection ──────────────────────────────────────────────────
    result = detect_anomaly(
        weekly_kwh     = payload.weekly_kwh,
        past_readings  = past_kwh,
        household_size = household_size,
        is_hot_season  = payload.is_hot_season,
        is_cold_season = payload.is_cold_season,
    )

    # ── Persist the weekly consumption record ─────────────────────────────────
    record = WeeklyConsumption(
        user_id          = current_user.id,
        dashboard_id     = payload.dashboard_id,
        week_number      = week_number,
        year             = year,
        weekly_kwh       = payload.weekly_kwh,
        avg_temperature  = payload.avg_temperature,
        is_hot_season    = payload.is_hot_season,
        is_cold_season   = payload.is_cold_season,
        is_hvac_week     = payload.is_hvac_week,
        household_size   = household_size,
        is_anomaly       = result["is_anomaly"],
        anomaly_type     = result["anomaly_type"],
        z_score          = result["z_score"],
        rolling_mean     = result["rolling_mean"],
        rolling_std      = result["rolling_std"],
        anomaly_detail   = result["detail"],
        notification_sent= False,
    )
    db.add(record)
    db.flush()  # get record.id before notification

    # ── Create in-app notification if anomaly detected ─────────────────────────
    notif_payload = build_notification(
        result,
        week_number = week_number,
        year        = year,
        username    = current_user.username,
    )
    if notif_payload:
        notif = Notification(
            user_id               = current_user.id,
            title                 = notif_payload["title"],
            message               = notif_payload["message"],
            level                 = notif_payload["level"],
            category              = "anomaly",
            weekly_consumption_id = record.id,
            extra_data            = {
                "z_score":       result["z_score"],
                "anomaly_type":  result["anomaly_type"],
                "weekly_kwh":    payload.weekly_kwh,
                "rolling_mean":  result["rolling_mean"],
            },
        )
        db.add(notif)
        record.notification_sent = True

    db.commit()
    db.refresh(record)
    return record


# ── GET – list history ─────────────────────────────────────────────────────────
@router.get("", response_model=WeeklyConsumptionList)
def list_weekly(
    dashboard_id:  Optional[int] = Query(None),
    anomaly_only:  bool          = Query(False, description="Return only anomalous weeks"),
    skip:          int           = Query(0,  ge=0),
    limit:         int           = Query(20, ge=1, le=100),
    db:            Session       = Depends(get_db),
    current_user:  User          = Depends(get_current_user),
):
    q = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.user_id == current_user.id
    )
    if dashboard_id is not None:
        q = q.filter(WeeklyConsumption.dashboard_id == dashboard_id)
    if anomaly_only:
        q = q.filter(WeeklyConsumption.is_anomaly == True)  # noqa: E712

    total     = q.count()
    anomalies = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.user_id  == current_user.id,
        WeeklyConsumption.is_anomaly == True,  # noqa: E712
    ).count()

    records = (
        q.order_by(WeeklyConsumption.year.desc(), WeeklyConsumption.week_number.desc())
        .offset(skip).limit(limit).all()
    )

    return WeeklyConsumptionList(items=records, total=total, anomalies=anomalies)


# ── GET /stats – MUST stay before /{record_id} ────────────────────────────────
# FastAPI matches routes in declaration order. If /{record_id} were first,
# a request to /stats would try to cast "stats" as int → 422 error.
@router.get("/stats")
def weekly_stats(
    dashboard_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.user_id == current_user.id
    )
    if dashboard_id is not None:
        q = q.filter(WeeklyConsumption.dashboard_id == dashboard_id)

    records = q.order_by(
        WeeklyConsumption.year.asc(), WeeklyConsumption.week_number.asc()
    ).all()

    if not records:
        return {"message": "No weekly data yet.", "total_weeks": 0}

    kwh_vals   = [r.weekly_kwh for r in records]
    n          = len(kwh_vals)
    mean       = sum(kwh_vals) / n
    variance   = sum((v - mean)**2 for v in kwh_vals) / n
    std        = variance ** 0.5
    anomalies  = [r for r in records if r.is_anomaly]

    return {
        "total_weeks":        n,
        "total_kwh":          round(sum(kwh_vals), 2),
        "avg_weekly_kwh":     round(mean, 2),
        "std_weekly_kwh":     round(std, 2),
        "min_weekly_kwh":     round(min(kwh_vals), 2),
        "max_weekly_kwh":     round(max(kwh_vals), 2),
        "anomaly_count":      len(anomalies),
        "anomaly_rate_pct":   round(100 * len(anomalies) / n, 1),
        "high_anomalies":     sum(1 for r in anomalies if r.anomaly_type == "high"),
        "low_anomalies":      sum(1 for r in anomalies if r.anomaly_type == "low"),
        "last_week_kwh":      round(kwh_vals[-1], 2),
        "last_week_anomaly":  records[-1].is_anomaly,
    }


# ── GET /{record_id} – single record  (declared AFTER /stats) ─────────────────
@router.get("/{record_id}", response_model=WeeklyConsumptionOut)
def get_weekly(
    record_id:    int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    record = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.id      == record_id,
        WeeklyConsumption.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


# ── DELETE /{id} ──────────────────────────────────────────────────────────────
@router.delete("/{record_id}", status_code=204)
def delete_weekly(
    record_id:    int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    record = db.query(WeeklyConsumption).filter(
        WeeklyConsumption.id      == record_id,
        WeeklyConsumption.user_id == current_user.id,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(record)
    db.commit()
