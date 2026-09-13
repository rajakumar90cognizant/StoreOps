"""Alerts business logic.

`handle_programme_member_added` is the EventBus subscriber wired up in
`app.main` at import time -- the concrete cross-module side effect this
architecture forces through the bus instead of a direct import from
`programmes.service`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.event_bus import Event
from app.modules.alerts.models import Notification, NotificationChannel, NotificationType
from app.modules.alerts.repository import alert_repository


class AlertService:
    def __init__(self) -> None:
        self._repository = alert_repository

    def list_for_user(self, user_id: str) -> list[Notification]:
        return [n for n in self._repository.list_all() if n.user_id == user_id]

    def create_notification(
        self,
        *,
        user_id: str,
        notification_type: NotificationType,
        message: str,
        source_module: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        notification = Notification(
            id=uuid4().hex,
            user_id=user_id,
            channel=channel,
            type=notification_type,
            message=message,
            source_module=source_module,
            created_at=datetime.now(UTC),
        )
        self._repository.add(notification)
        return notification

    def handle_programme_member_added(self, event: Event) -> None:
        """Subscriber for `programme.member_added` (see app.main wiring)."""
        programme_name = event.payload["programme_name"]
        self.create_notification(
            user_id=event.payload["user_id"],
            notification_type=NotificationType.SHIFT_HANDOVER,
            message=f"You were added to programme '{programme_name}'.",
            source_module="programmes",
        )

    def handle_activity_bulk_status_updated(self, event: Event) -> None:
        """Subscriber for `activity.bulk_status_updated` (see app.main wiring).

        Creates a shift-handover audit-entry notification for the task's
        owner only -- never the assignee (see sprint-2 non-goals).
        """
        task_id = event.payload["task_id"]
        new_status = event.payload["new_status"]
        self.create_notification(
            user_id=event.payload["owner_id"],
            notification_type=NotificationType.SHIFT_HANDOVER,
            message=f"Task '{task_id}' status changed to '{new_status}'.",
            source_module="activities",
        )


alert_service = AlertService()
