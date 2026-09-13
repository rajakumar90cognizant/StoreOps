"""Alerts domain models -- in-app notifications triggered by operational events."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class NotificationType(StrEnum):
    INVENTORY = "INVENTORY"
    SLA_BREACH = "SLA_BREACH"
    SHIFT_HANDOVER = "SHIFT_HANDOVER"
    ESCALATION = "ESCALATION"


class NotificationStatus(StrEnum):
    UNREAD = "UNREAD"
    READ = "READ"


class Notification(BaseModel):
    id: str
    user_id: str
    channel: NotificationChannel
    type: NotificationType
    message: str
    status: NotificationStatus = NotificationStatus.UNREAD
    source_module: str
    created_at: datetime


class NotificationOut(BaseModel):
    id: str
    user_id: str
    channel: NotificationChannel
    type: NotificationType
    message: str
    status: NotificationStatus
    source_module: str
    created_at: datetime

    @classmethod
    def from_notification(cls, notification: Notification) -> NotificationOut:
        return cls(**notification.model_dump())
