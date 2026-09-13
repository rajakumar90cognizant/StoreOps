"""Activities HTTP layer -- request/response validation and shaping only.

No business logic lives here: every route delegates straight to
`activity_service`. That is the layering rule this project enforces --
Routes -> Service -> Repository, never skipped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import get_current_user
from app.modules.activities.models import (
    BulkStatusUpdateRequest,
    BulkStatusUpdateResponse,
    TaskCreate,
    TaskOut,
    TaskStatus,
    TaskUpdate,
)
from app.modules.activities.service import activity_service
from app.modules.staff.models import User

router = APIRouter(prefix="/api/activities", tags=["activities"])


@router.get("", response_model=list[TaskOut])
def list_activities(
    programme_id: str | None = Query(default=None),
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
) -> list[TaskOut]:
    tasks = activity_service.list_activities(programme_id=programme_id, status=status_filter)
    return [TaskOut.from_task(task) for task in tasks]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_activity(payload: TaskCreate, current_user: User = Depends(get_current_user)) -> TaskOut:
    task = activity_service.create_activity(payload, owner=current_user)
    return TaskOut.from_task(task)


@router.patch("/bulk-status", response_model=BulkStatusUpdateResponse)
def bulk_update_status(
    payload: BulkStatusUpdateRequest, current_user: User = Depends(get_current_user)
) -> BulkStatusUpdateResponse:
    return activity_service.bulk_update_status(payload, actor=current_user)


@router.get("/{task_id}", response_model=TaskOut)
def get_activity(task_id: str) -> TaskOut:
    task = activity_service.get_activity(task_id)
    return TaskOut.from_task(task)


@router.patch("/{task_id}", response_model=TaskOut)
def update_activity(
    task_id: str,
    payload: TaskUpdate,
    # current_user is intentionally unused below -- this dependency exists only
    # to require a valid bearer token, matching the other mutating endpoints.
    current_user: User = Depends(get_current_user),
) -> TaskOut:
    task = activity_service.update_activity(task_id, payload)
    return TaskOut.from_task(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(task_id: str, current_user: User = Depends(get_current_user)) -> None:
    activity_service.delete_activity(task_id, requester=current_user)
