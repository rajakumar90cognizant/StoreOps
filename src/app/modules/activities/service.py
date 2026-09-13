"""Activities business logic.

Reads staff via `staff_service` (service-to-service, allowed for reads).
Never imports `app.modules.staff.repository` directly -- that would be the
module-boundary violation this harness exists to prevent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.event_bus import event_bus
from app.modules.activities.models import (
    BulkStatusFailure,
    BulkStatusUpdateRequest,
    BulkStatusUpdateResponse,
    Task,
    TaskCreate,
    TaskOut,
    TaskStatus,
    TaskUpdate,
)
from app.modules.activities.repository import activity_repository
from app.modules.staff.models import StaffRole, User
from app.modules.staff.service import staff_service

BULK_STATUS_UPDATED_EVENT = "activity.bulk_status_updated"


class ActivityService:
    def __init__(self) -> None:
        self._repository = activity_repository
        self._staff = staff_service

    def list_activities(
        self, *, programme_id: str | None = None, status: TaskStatus | None = None
    ) -> list[Task]:
        tasks = self._repository.list_all()
        if programme_id is not None:
            tasks = [t for t in tasks if t.programme_id == programme_id]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_activity(self, task_id: str) -> Task:
        return self._repository.get(task_id)

    def create_activity(self, payload: TaskCreate, *, owner: User) -> Task:
        if payload.assignee_id is not None:
            self._require_valid_assignee(payload.assignee_id)
        now = datetime.now(UTC)
        task = Task(
            id=uuid4().hex,
            store_id=owner.store_id,
            programme_id=payload.programme_id,
            title=payload.title,
            description=payload.description,
            status=TaskStatus.TODO,
            priority=payload.priority,
            category=payload.category,
            assignee_id=payload.assignee_id,
            owner_id=owner.id,
            created_at=now,
            updated_at=now,
        )
        self._repository.add(task)
        return task

    def update_activity(self, task_id: str, payload: TaskUpdate) -> Task:
        task = self._repository.get(task_id)
        if payload.assignee_id is not None:
            self._require_valid_assignee(payload.assignee_id)
        changes = payload.model_dump(exclude_unset=True)
        changes["updated_at"] = datetime.now(UTC)
        updated = task.model_copy(update=changes)
        self._repository.update(updated)
        return updated

    def bulk_update_status(
        self, payload: BulkStatusUpdateRequest, *, actor: User
    ) -> BulkStatusUpdateResponse:
        if not payload.updates:
            raise ValidationError(
                "updates must contain at least one item",
                details={"updates": payload.updates},
            )
        updated: list[Task] = []
        failures: list[BulkStatusFailure] = []
        for item in payload.updates:
            try:
                task = self._repository.get(item.task_id)
            except NotFoundError as exc:
                failures.append(
                    BulkStatusFailure(
                        task_id=item.task_id,
                        code=exc.code,
                        message=exc.message,
                    )
                )
                continue
            previous_status = task.status
            changes = {"status": item.status, "updated_at": datetime.now(UTC)}
            updated_task = task.model_copy(update=changes)
            self._repository.update(updated_task)
            updated.append(updated_task)
            event_bus.emit(
                BULK_STATUS_UPDATED_EVENT,
                {
                    "task_id": updated_task.id,
                    "store_id": updated_task.store_id,
                    "owner_id": updated_task.owner_id,
                    "assignee_id": updated_task.assignee_id,
                    "previous_status": previous_status.value,
                    "new_status": updated_task.status.value,
                    "actor_id": actor.id,
                },
            )
        return BulkStatusUpdateResponse(
            updated=[TaskOut.from_task(task) for task in updated],
            failures=failures,
        )

    def delete_activity(self, task_id: str, *, requester: User) -> None:
        task = self._repository.get(task_id)
        is_owner = task.owner_id == requester.id
        is_store_manager = requester.staff_role in (
            StaffRole.STORE_MANAGER,
            StaffRole.REGIONAL_MANAGER,
        )
        if not (is_owner or is_store_manager):
            raise ForbiddenError(
                "Only the activity's owner or a store manager may delete it",
                details={"task_id": task_id, "requester_id": requester.id},
            )
        self._repository.delete(task_id)

    def _require_valid_assignee(self, assignee_id: str) -> None:
        try:
            self._staff.get_user(assignee_id)
        except NotFoundError as exc:
            raise ValidationError(
                "assignee_id does not refer to a known staff member",
                details={"assignee_id": assignee_id},
            ) from exc


activity_service = ActivityService()
