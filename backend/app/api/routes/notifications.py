"""
Notifications routes
====================
GET    /api/notifications/           — list all (paginated, filterable)
GET    /api/notifications/unread     — unread count  ← MUST be before /{id}/read
PATCH  /api/notifications/read-all   — mark all as read  ← MUST be before /{id}/read
PATCH  /api/notifications/{id}/read  — mark one as read
DELETE /api/notifications/{id}       — delete one notification

Route ordering rule: static paths (/unread, /read-all) MUST come before
parameterised paths (/{notif_id}/...) otherwise FastAPI matches the param
route first and tries to cast "unread" or "read-all" as an integer → 404/422.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.schemas import NotificationOut, NotificationList

router = APIRouter()


# ── GET / – list notifications ─────────────────────────────────────────────────
@router.get("", response_model=NotificationList)
def list_notifications(
    unread_only:  bool          = Query(False),
    level:        Optional[str] = Query(None, description="info | warning | critical"),
    skip:         int           = Query(0,  ge=0),
    limit:        int           = Query(20, ge=1, le=100),
    db:           Session       = Depends(get_db),
    current_user: User          = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    if level:
        q = q.filter(Notification.level == level)

    total  = q.count()
    unread = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).count()

    items = q.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    return NotificationList(items=items, total=total, unread=unread)


# ── GET /unread – badge count  (BEFORE /{notif_id} routes) ────────────────────
@router.get("/unread")
def unread_count(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).count()
    return {"unread": count}


# ── PATCH /read-all  (BEFORE /{notif_id} routes) ──────────────────────────────
@router.patch("/read-all")
def mark_all_read(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    now     = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .all()
    )
    for n in updated:
        n.is_read = True
        n.read_at = now
    db.commit()
    return {"marked_read": len(updated)}


# ── PATCH /{notif_id}/read ─────────────────────────────────────────────────────
@router.patch("/{notif_id}/read", response_model=NotificationOut)
def mark_read(
    notif_id:     int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id      == notif_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if not notif.is_read:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)
    return notif


# ── DELETE /{notif_id} ─────────────────────────────────────────────────────────
@router.delete("/{notif_id}", status_code=204)
def delete_notification(
    notif_id:     int,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    notif = db.query(Notification).filter(
        Notification.id      == notif_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(notif)
    db.commit()
