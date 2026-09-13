"""Programmes domain models -- store programmes and their staff membership."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ProjectRole(StrEnum):
    STORE_MANAGER = "STORE_MANAGER"
    DEPARTMENT_LEAD = "DEPARTMENT_LEAD"
    ASSOCIATE = "ASSOCIATE"


class ProjectMember(BaseModel):
    user_id: str
    role: ProjectRole


class Project(BaseModel):
    id: str
    store_id: str
    name: str
    description: str | None = None
    members: list[ProjectMember] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: str
    role: ProjectRole = ProjectRole.ASSOCIATE


class ProjectOut(BaseModel):
    id: str
    store_id: str
    name: str
    description: str | None
    members: list[ProjectMember]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_project(cls, project: Project) -> ProjectOut:
        return cls(**project.model_dump())
