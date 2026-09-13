"""In-memory reports repository."""

from __future__ import annotations

from app.core.repository import InMemoryRepository
from app.modules.reports.models import Report


class ReportRepository:
    def __init__(self) -> None:
        self._store = InMemoryRepository[Report](not_found_message="Report not found")

    def add(self, report: Report) -> str:
        return self._store.add(report, item_id=report.id)

    def list_all(self) -> list[Report]:
        return self._store.list_all()

    def clear(self) -> None:
        self._store.clear()


report_repository = ReportRepository()
