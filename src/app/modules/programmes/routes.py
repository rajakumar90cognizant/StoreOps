"""Programmes HTTP layer -- validation and shaping only, no business logic."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.modules.programmes.models import ProjectCreate, ProjectMemberCreate, ProjectOut
from app.modules.programmes.service import programme_service
from app.modules.staff.models import User

router = APIRouter(prefix="/api/programmes", tags=["programmes"])


@router.get("", response_model=list[ProjectOut])
def list_programmes(current_user: User = Depends(get_current_user)) -> list[ProjectOut]:
    projects = programme_service.list_programmes(store_id=current_user.store_id)
    return [ProjectOut.from_project(p) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_programme(
    payload: ProjectCreate, current_user: User = Depends(get_current_user)
) -> ProjectOut:
    project = programme_service.create_programme(payload, owner=current_user)
    return ProjectOut.from_project(project)


@router.post(
    "/{programme_id}/members", response_model=ProjectOut, status_code=status.HTTP_201_CREATED
)
def add_member(
    programme_id: str,
    payload: ProjectMemberCreate,
    # current_user is intentionally unused below -- this dependency exists only
    # to require a valid bearer token, matching the other mutating endpoints.
    current_user: User = Depends(get_current_user),
) -> ProjectOut:
    project = programme_service.add_member(programme_id, payload)
    return ProjectOut.from_project(project)
