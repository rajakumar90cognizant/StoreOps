"""Activities domain models -- restocking runs, planogram resets, audits, general tasks."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"


class TaskPriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskCategory(StrEnum):
    RESTOCKING = "RESTOCKING"
    PLANOGRAM = "PLANOGRAM"
    AUDIT = "AUDIT"
    COMPLIANCE = "COMPLIANCE"
    GENERAL = "GENERAL"


class Task(BaseModel):
    """The stored domain entity."""

    id: str
    store_id: str
    programme_id: str | None = None
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    category: TaskCategory = TaskCategory.GENERAL
    assignee_id: str | None = None
    owner_id: str
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    """Request body for POST /api/activities."""

    title: str
    description: str | None = None
    programme_id: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    category: TaskCategory = TaskCategory.GENERAL
    assignee_id: str | None = None


class TaskUpdate(BaseModel):
    """Request body for PATCH /api/activities/{id}. Only set fields are applied."""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    category: TaskCategory | None = None
    assignee_id: str | None = None


class TaskOut(BaseModel):
    """Response shape for activities endpoints."""

    id: str
    store_id: str
    programme_id: str | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    category: TaskCategory
    assignee_id: str | None
    owner_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: Task) -> TaskOut:
        return cls(**task.model_dump())


class BulkStatusUpdateItem(BaseModel):
    """One item within a `PATCH /api/activities/bulk-status` request body."""

    task_id: str
    status: Literal[TaskStatus.DONE, TaskStatus.BLOCKED]


class BulkStatusUpdateRequest(BaseModel):
    """Request body for PATCH /api/activities/bulk-status."""

    updates: list[BulkStatusUpdateItem] = Field(default_factory=list)


class BulkStatusFailure(BaseModel):
    """One failed item in a bulk status update response."""

    task_id: str
    code: str
    message: str


class BulkStatusUpdateResponse(BaseModel):
    """Response shape for PATCH /api/activities/bulk-status."""

    updated: list[TaskOut] = Field(default_factory=list)
    failures: list[BulkStatusFailure] = Field(default_factory=list)
