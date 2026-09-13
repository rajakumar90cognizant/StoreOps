"""In-memory alerts repository."""

from __future__ import annotations

from app.core.repository import InMemoryRepository
from app.modules.alerts.models import Notification


class AlertRepository:
    def __init__(self) -> None:
        self._store = InMemoryRepository[Notification](not_found_message="Notification not found")

    def add(self, notification: Notification) -> str:
        return self._store.add(notification, item_id=notification.id)

    def list_all(self) -> list[Notification]:
        return self._store.list_all()

    def clear(self) -> None:
        self._store.clear()


alert_repository = AlertRepository()
