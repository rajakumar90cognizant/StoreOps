"""Programmes business logic.

Adding a member is the one place in the baseline that must raise a
cross-module side effect through the event bus: `alerts.service`
subscribes to `programme.member_added` (wired in `app.main`) and creates
an IN_APP notification for the new member. This service must never import
`app.modules.alerts.service` directly for that -- doing so would be
exactly the failure mode ("missing event bus integration") this project
exists to prevent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.event_bus import event_bus
from app.modules.programmes.models import (
    Project,
    ProjectCreate,
    ProjectMember,
    ProjectMemberCreate,
)
from app.modules.programmes.repository import programme_repository
from app.modules.staff.models import User
from app.modules.staff.service import staff_service

MEMBER_ADDED_EVENT = "programme.member_added"


class ProgrammeService:
    def __init__(self) -> None:
        self._repository = programme_repository
        self._staff = staff_service

    def list_programmes(self, *, store_id: str) -> list[Project]:
        return [p for p in self._repository.list_all() if p.store_id == store_id]

    def create_programme(self, payload: ProjectCreate, *, owner: User) -> Project:
        now = datetime.now(UTC)
        project = Project(
            id=uuid4().hex,
            store_id=owner.store_id,
            name=payload.name,
            description=payload.description,
            created_at=now,
            updated_at=now,
        )
        self._repository.add(project)
        return project

    def add_member(self, programme_id: str, payload: ProjectMemberCreate) -> Project:
        project = self._repository.get(programme_id)
        try:
            member_user = self._staff.get_user(payload.user_id)
        except NotFoundError as exc:
            raise ValidationError(
                "user_id does not refer to a known staff member",
                details={"user_id": payload.user_id},
            ) from exc
        if any(m.user_id == payload.user_id for m in project.members):
            raise ConflictError(
                "Staff member is already on this programme",
                details={"programme_id": programme_id, "user_id": payload.user_id},
            )
        updated_project = project.model_copy(
            update={
                "members": [
                    *project.members,
                    ProjectMember(user_id=payload.user_id, role=payload.role),
                ],
                "updated_at": datetime.now(UTC),
            }
        )
        self._repository.update(updated_project)
        event_bus.emit(
            MEMBER_ADDED_EVENT,
            {
                "programme_id": programme_id,
                "programme_name": updated_project.name,
                "user_id": member_user.id,
                "role": payload.role.value,
            },
        )
        return updated_project


programme_service = ProgrammeService()
