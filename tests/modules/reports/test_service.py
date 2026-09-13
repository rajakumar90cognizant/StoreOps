"""Reports service tests -- read-only aggregation across other modules."""

from __future__ import annotations

from app.modules.activities.models import TaskCreate
from app.modules.activities.service import activity_service
from app.modules.programmes.models import ProjectCreate
from app.modules.programmes.service import programme_service
from app.modules.reports.models import ReportStatus, ReportType
from app.modules.reports.service import report_service
from app.modules.staff.service import staff_service


def test_build_store_summary_counts_programmes_and_tasks_for_that_store() -> None:
    owner = staff_service.get_user("user-store-manager")
    programme_service.create_programme(ProjectCreate(name="Reset"), owner=owner)
    activity_service.create_activity(TaskCreate(title="Restock"), owner=owner)

    report = report_service.build_store_summary(owner.store_id)

    assert report.type == ReportType.STORE_SUMMARY
    assert report.status == ReportStatus.READY
    assert report.payload["programme_count"] >= 1
    assert report.payload["task_count"] >= 1


def test_build_store_summary_counts_completed_tasks_separately() -> None:
    from app.modules.activities.models import TaskStatus, TaskUpdate

    owner = staff_service.get_user("user-store-manager")
    task = activity_service.create_activity(TaskCreate(title="Audit"), owner=owner)
    activity_service.update_activity(task.id, TaskUpdate(status=TaskStatus.DONE))

    report = report_service.build_store_summary(owner.store_id)

    assert report.payload["completed_task_count"] >= 1
