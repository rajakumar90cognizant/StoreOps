"""In-memory programmes repository."""

from __future__ import annotations

from app.core.repository import InMemoryRepository
from app.modules.programmes.models import Project


class ProgrammeRepository:
    def __init__(self) -> None:
        self._store = InMemoryRepository[Project](not_found_message="Programme not found")

    def add(self, project: Project) -> str:
        return self._store.add(project, item_id=project.id)

    def get(self, project_id: str) -> Project:
        return self._store.get(project_id)

    def list_all(self) -> list[Project]:
        return self._store.list_all()

    def update(self, project: Project) -> None:
        self._store.set(project.id, project)

    def clear(self) -> None:
        self._store.clear()


programme_repository = ProgrammeRepository()
