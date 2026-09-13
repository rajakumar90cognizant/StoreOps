"""Alerts HTTP layer -- validation and shaping only, no business logic."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.modules.alerts.models import NotificationOut
from app.modules.alerts.service import alert_service
from app.modules.staff.models import User

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[NotificationOut])
def list_alerts(current_user: User = Depends(get_current_user)) -> list[NotificationOut]:
    notifications = alert_service.list_for_user(current_user.id)
    return [NotificationOut.from_notification(n) for n in notifications]
