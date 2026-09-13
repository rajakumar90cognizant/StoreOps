"""Alerts route tests."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.alerts.models import NotificationType
from app.modules.alerts.service import alert_service


async def test_list_alerts_returns_only_authenticated_users_notifications(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    alert_service.create_notification(
        user_id="user-associate",
        notification_type=NotificationType.ESCALATION,
        message="Escalated to you",
        source_module="activities",
    )

    resp = await client.get("/api/alerts", headers=associate_headers)

    assert resp.status_code == 200
    assert any(n["message"] == "Escalated to you" for n in resp.json())


async def test_list_alerts_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/alerts")

    assert resp.status_code == 401
