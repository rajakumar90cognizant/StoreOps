"""Reports business logic.

Read-only by architecture rule: this service only ever calls into
`activities.service` and `programmes.service` for data (both are
service-layer reads, which are allowed across module boundaries). There is
no method anywhere in this module that writes to another module's service
or repository -- `reports` aggregates, it never writes back. No public
routes are mounted for this module in the baseline; the base API surface
(Section 3.6 of the capstone spec) does not include a reports endpoint, so
this layer exists and is tested but is wired up when a reporting feature
is actually requested (see the demonstration-run harness).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.modules.activities.models import TaskStatus
from app.modules.activities.service import activity_service
from app.modules.programmes.service import programme_service
from app.modules.reports.models import Report, ReportStatus, ReportType
from app.modules.reports.repository import report_repository


class ReportService:
    def __init__(self) -> None:
        self._repository = report_repository

    def build_store_summary(self, store_id: str) -> Report:
        programmes = programme_service.list_programmes(store_id=store_id)
        tasks = [t for t in activity_service.list_activities() if t.store_id == store_id]
        completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        payload = {
            "programme_count": len(programmes),
            "task_count": len(tasks),
            "completed_task_count": completed,
        }
        report = Report(
            id=uuid4().hex,
            type=ReportType.STORE_SUMMARY,
            status=ReportStatus.READY,
            store_id=store_id,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        self._repository.add(report)
        return report


report_service = ReportService()
