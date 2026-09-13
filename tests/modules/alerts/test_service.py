"""Alerts service tests."""

from __future__ import annotations

from app.core.event_bus import Event
from app.modules.alerts.models import NotificationChannel, NotificationType
from app.modules.alerts.service import alert_service


def test_create_notification_defaults_to_unread_and_in_app() -> None:
    notification = alert_service.create_notification(
        user_id="user-associate",
        notification_type=NotificationType.INVENTORY,
        message="Low stock on aisle 4",
        source_module="activities",
    )

    assert notification.status == "UNREAD"
    assert notification.channel == NotificationChannel.IN_APP


def test_list_for_user_only_returns_that_users_notifications() -> None:
    alert_service.create_notification(
        user_id="user-associate",
        notification_type=NotificationType.SLA_BREACH,
        message="Task overdue",
        source_module="activities",
    )
    alert_service.create_notification(
        user_id="user-dept-lead",
        notification_type=NotificationType.SLA_BREACH,
        message="Different user's task",
        source_module="activities",
    )

    associate_alerts = alert_service.list_for_user("user-associate")

    assert all(n.user_id == "user-associate" for n in associate_alerts)
    assert any(n.message == "Task overdue" for n in associate_alerts)


def test_handle_programme_member_added_creates_shift_handover_notification() -> None:
    event = Event(
        name="programme.member_added",
        payload={"programme_name": "Winter Reset", "user_id": "user-associate"},
    )

    alert_service.handle_programme_member_added(event)

    notifications = alert_service.list_for_user("user-associate")
    assert any(n.type == NotificationType.SHIFT_HANDOVER for n in notifications)


def _bulk_status_updated_event(
    *, task_id: str, owner_id: str = "user-associate"
) -> Event:
    return Event(
        name="activity.bulk_status_updated",
        payload={
            "task_id": task_id,
            "store_id": "store-1",
            "owner_id": owner_id,
            "assignee_id": None,
            "previous_status": "TODO",
            "new_status": "DONE",
            "actor_id": "user-store-manager",
        },
    )


def test_handle_activity_bulk_status_updated_creates_one_shift_handover_notification() -> None:
    event = _bulk_status_updated_event(task_id="task-1")

    alert_service.handle_activity_bulk_status_updated(event)

    notifications = [
        n
        for n in alert_service.list_for_user("user-associate")
        if n.type == NotificationType.SHIFT_HANDOVER and n.source_module == "activities"
    ]
    assert len(notifications) == 1


def test_handle_activity_bulk_status_updated_creates_one_audit_entry_per_task() -> None:
    alert_service.handle_activity_bulk_status_updated(
        _bulk_status_updated_event(task_id="task-1")
    )
    alert_service.handle_activity_bulk_status_updated(
        _bulk_status_updated_event(task_id="task-2")
    )

    notifications = [
        n
        for n in alert_service.list_for_user("user-associate")
        if n.type == NotificationType.SHIFT_HANDOVER and n.source_module == "activities"
    ]
    assert len(notifications) == 2
    assert any("task-1" in n.message for n in notifications)
    assert any("task-2" in n.message for n in notifications)


def test_bulk_update_status_end_to_end_fires_shift_handover_notification() -> None:
    # Importing app.main executes its module-level event_bus.subscribe wiring,
    # which is the only place activities and alerts are ever coupled.
    import app.main  # noqa: F401
    from app.modules.activities.models import (
        BulkStatusUpdateItem,
        BulkStatusUpdateRequest,
        TaskCreate,
        TaskStatus,
    )
    from app.modules.activities.service import activity_service
    from app.modules.staff.service import staff_service

    owner = staff_service.get_user("user-associate")
    actor = staff_service.get_user("user-store-manager")
    task = activity_service.create_activity(TaskCreate(title="Restock aisle 4"), owner=owner)

    activity_service.bulk_update_status(
        BulkStatusUpdateRequest(
            updates=[BulkStatusUpdateItem(task_id=task.id, status=TaskStatus.DONE)]
        ),
        actor=actor,
    )

    notifications = [
        n
        for n in alert_service.list_for_user("user-associate")
        if n.type == NotificationType.SHIFT_HANDOVER and n.source_module == "activities"
    ]
    assert any(task.id in n.message for n in notifications)


def test_bulk_update_status_end_to_end_skips_notification_for_failed_item() -> None:
    import app.main  # noqa: F401
    from app.modules.activities.models import (
        BulkStatusUpdateItem,
        BulkStatusUpdateRequest,
        TaskCreate,
        TaskStatus,
    )
    from app.modules.activities.service import activity_service
    from app.modules.staff.service import staff_service

    owner = staff_service.get_user("user-associate")
    actor = staff_service.get_user("user-store-manager")
    task = activity_service.create_activity(TaskCreate(title="Planogram reset"), owner=owner)

    result = activity_service.bulk_update_status(
        BulkStatusUpdateRequest(
            updates=[
                BulkStatusUpdateItem(task_id=task.id, status=TaskStatus.DONE),
                BulkStatusUpdateItem(task_id="ghost-task", status=TaskStatus.DONE),
            ]
        ),
        actor=actor,
    )

    assert len(result.failures) == 1
    assert result.failures[0].task_id == "ghost-task"

    notifications = [
        n
        for n in alert_service.list_for_user("user-associate")
        if n.type == NotificationType.SHIFT_HANDOVER and n.source_module == "activities"
    ]
    assert len(notifications) == 1
    assert task.id in notifications[0].message
    assert not any("ghost-task" in n.message for n in notifications)
