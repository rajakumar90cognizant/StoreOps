"""Programmes service tests, including the event-bus side effect."""

from __future__ import annotations

import pytest

from app.core.errors import ConflictError, ValidationError
from app.modules.alerts.service import alert_service
from app.modules.programmes.models import ProjectCreate, ProjectMemberCreate, ProjectRole
from app.modules.programmes.service import programme_service
from app.modules.staff.service import staff_service


def test_create_programme_belongs_to_owners_store() -> None:
    owner = staff_service.get_user("user-store-manager")

    project = programme_service.create_programme(ProjectCreate(name="Winter Reset"), owner=owner)

    assert project.store_id == owner.store_id
    assert project.members == []


def test_add_member_updates_project_and_fires_notification_via_event_bus() -> None:
    owner = staff_service.get_user("user-store-manager")
    associate = staff_service.get_user("user-associate")
    project = programme_service.create_programme(
        ProjectCreate(name="Compliance Drive"), owner=owner
    )

    updated = programme_service.add_member(
        project.id, ProjectMemberCreate(user_id=associate.id, role=ProjectRole.ASSOCIATE)
    )

    assert any(m.user_id == associate.id for m in updated.members)

    # cross-module side effect: alerts received this via EventBus.emit, not a direct call
    notifications = alert_service.list_for_user(associate.id)
    assert any(n.source_module == "programmes" for n in notifications)


def test_add_member_twice_is_a_conflict() -> None:
    owner = staff_service.get_user("user-store-manager")
    associate = staff_service.get_user("user-associate")
    project = programme_service.create_programme(ProjectCreate(name="Refit"), owner=owner)
    programme_service.add_member(project.id, ProjectMemberCreate(user_id=associate.id))

    with pytest.raises(ConflictError):
        programme_service.add_member(project.id, ProjectMemberCreate(user_id=associate.id))


def test_add_member_rejects_unknown_user() -> None:
    owner = staff_service.get_user("user-store-manager")
    project = programme_service.create_programme(ProjectCreate(name="Audit Sprint"), owner=owner)

    with pytest.raises(ValidationError):
        programme_service.add_member(project.id, ProjectMemberCreate(user_id="ghost"))
