"""Shared pytest fixtures.

`_reset_state` clears every module's in-memory store before each test so
tests don't leak state into each other -- except `staff`, whose seeded
demo users and tokens are meant to persist for the whole run; every other
fixture (auth headers) depends on that seed data staying put.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.activities.repository import activity_repository
from app.modules.alerts.repository import alert_repository
from app.modules.programmes.repository import programme_repository
from app.modules.reports.repository import report_repository

STORE_MANAGER_TOKEN = "demo-store-manager-token"
DEPARTMENT_LEAD_TOKEN = "demo-dept-lead-token"
ASSOCIATE_TOKEN = "demo-associate-token"


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    activity_repository.clear()
    programme_repository.clear()
    alert_repository.clear()
    report_repository.clear()


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def store_manager_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {STORE_MANAGER_TOKEN}"}


@pytest.fixture
def dept_lead_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {DEPARTMENT_LEAD_TOKEN}"}


@pytest.fixture
def associate_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ASSOCIATE_TOKEN}"}
