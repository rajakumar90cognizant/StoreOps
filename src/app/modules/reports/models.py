"""Reports domain models -- store and regional performance summaries."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(StrEnum):
    STORE_SUMMARY = "STORE_SUMMARY"
    REGIONAL_ROLLUP = "REGIONAL_ROLLUP"
    DEPARTMENT_PERFORMANCE = "DEPARTMENT_PERFORMANCE"


class ReportStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"


class Report(BaseModel):
    id: str
    type: ReportType
    status: ReportStatus = ReportStatus.PENDING
    store_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
