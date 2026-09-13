"""Activities service tests -- assert domain state changes and typed errors,
never just an HTTP status code."""

from __future__ import annotations

import pytest

from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.core.event_bus import Event, event_bus
from app.modules.activities.models import (
    BulkStatusUpdateItem,
    BulkStatusUpdateRequest,
    TaskCategory,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)
from app.modules.activities.service import BULK_STATUS_UPDATED_EVENT, activity_service
from app.modules.staff.models import User
from app.modules.staff.service import staff_service


def _user(user_id: str = "user-associate") -> User:
    return staff_service.get_user(user_id)


def test_create_activity_defaults_to_todo_status() -> None:
    owner = _user()

    task = activity_service.create_activity(TaskCreate(title="Restock aisle 4"), owner=owner)

    assert task.status == TaskStatus.TODO
    assert task.owner_id == owner.id
    assert task.store_id == owner.store_id


def test_create_activity_rejects_unknown_assignee() -> None:
    owner = _user()

    with pytest.raises(ValidationError):
        activity_service.create_activity(
            TaskCreate(title="Audit", assignee_id="does-not-exist"), owner=owner
        )


def test_update_activity_changes_status_and_leaves_other_fields() -> None:
    owner = _user()
    task = activity_service.create_activity(
        TaskCreate(title="Planogram reset", category=TaskCategory.PLANOGRAM), owner=owner
    )

    updated = activity_service.update_activity(task.id, TaskUpdate(status=TaskStatus.DONE))

    assert updated.status == TaskStatus.DONE
    assert updated.category == TaskCategory.PLANOGRAM  # unrelated field untouched


def test_list_activities_filters_by_status() -> None:
    owner = _user()
    todo_task = activity_service.create_activity(TaskCreate(title="A"), owner=owner)
    done_task = activity_service.create_activity(TaskCreate(title="B"), owner=owner)
    activity_service.update_activity(done_task.id, TaskUpdate(status=TaskStatus.DONE))

    done_only = activity_service.list_activities(status=TaskStatus.DONE)

    done_ids = [t.id for t in done_only]
    assert done_task.id in done_ids
    assert todo_task.id not in done_ids


def test_delete_activity_by_owner_removes_it() -> None:
    owner = _user()
    task = activity_service.create_activity(TaskCreate(title="Compliance check"), owner=owner)

    activity_service.delete_activity(task.id, requester=owner)

    with pytest.raises(NotFoundError):
        activity_service.get_activity(task.id)


def test_delete_activity_by_store_manager_who_is_not_owner_succeeds() -> None:
    owner = _user("user-associate")
    store_manager = _user("user-store-manager")
    task = activity_service.create_activity(TaskCreate(title="Escalated audit"), owner=owner)

    activity_service.delete_activity(task.id, requester=store_manager)

    with pytest.raises(NotFoundError):
        activity_service.get_activity(task.id)


def test_delete_activity_by_non_owner_non_manager_is_forbidden() -> None:
    owner = _user("user-associate")
    dept_lead = _user("user-dept-lead")
    task = activity_service.create_activity(TaskCreate(title="Restock"), owner=owner)

    with pytest.raises(ForbiddenError):
        activity_service.delete_activity(task.id, requester=dept_lead)

    # business rule check, not just the exception type: the task must still exist
    assert activity_service.get_activity(task.id).id == task.id


def test_bulk_update_status_partial_failure_updates_valid_tasks_and_reports_ghost() -> None:
    owner = _user()
    task_a = activity_service.create_activity(TaskCreate(title="A"), owner=owner)
    task_b = activity_service.create_activity(TaskCreate(title="B"), owner=owner)

    result = activity_service.bulk_update_status(
        BulkStatusUpdateRequest(
            updates=[
                BulkStatusUpdateItem(task_id=task_a.id, status=TaskStatus.DONE),
                BulkStatusUpdateItem(task_id=task_b.id, status=TaskStatus.BLOCKED),
                BulkStatusUpdateItem(task_id="ghost", status=TaskStatus.DONE),
            ]
        ),
        actor=owner,
    )

    assert activity_service.get_activity(task_a.id).status == TaskStatus.DONE
    assert activity_service.get_activity(task_b.id).status == TaskStatus.BLOCKED
    assert len(result.updated) == 2
    assert len(result.failures) == 1
    assert result.failures[0].task_id == "ghost"
    assert result.failures[0].code == "NOT_FOUND"


def test_bulk_update_status_emits_one_event_per_successful_update() -> None:
    owner = _user("user-associate")
    actor = _user("user-store-manager")
    task = activity_service.create_activity(TaskCreate(title="Escalated"), owner=owner)

    captured: list[Event] = []
    event_bus.subscribe(BULK_STATUS_UPDATED_EVENT, captured.append)

    activity_service.bulk_update_status(
        BulkStatusUpdateRequest(
            updates=[BulkStatusUpdateItem(task_id=task.id, status=TaskStatus.BLOCKED)]
        ),
        actor=actor,
    )

    assert len(captured) == 1
    payload = captured[0].payload
    assert payload["task_id"] == task.id
    assert payload["previous_status"] == "TODO"
    assert payload["new_status"] == "BLOCKED"
    assert payload["owner_id"] == "user-associate"
    assert payload["actor_id"] == "user-store-manager"


def test_bulk_update_status_rejects_empty_updates_with_no_side_effects() -> None:
    owner = _user()

    captured: list[Event] = []
    event_bus.subscribe(BULK_STATUS_UPDATED_EVENT, captured.append)

    with pytest.raises(ValidationError):
        activity_service.bulk_update_status(BulkStatusUpdateRequest(updates=[]), actor=owner)

    assert captured == []
