"""In-memory activities repository."""

from __future__ import annotations

from app.core.repository import InMemoryRepository
from app.modules.activities.models import Task


class ActivityRepository:
    def __init__(self) -> None:
        self._store = InMemoryRepository[Task](not_found_message="Activity not found")

    def add(self, task: Task) -> str:
        return self._store.add(task, item_id=task.id)

    def get(self, task_id: str) -> Task:
        return self._store.get(task_id)

    def list_all(self) -> list[Task]:
        return self._store.list_all()

    def update(self, task: Task) -> None:
        self._store.set(task.id, task)

    def delete(self, task_id: str) -> None:
        self._store.delete(task_id)

    def clear(self) -> None:
        self._store.clear()


activity_repository = ActivityRepository()
