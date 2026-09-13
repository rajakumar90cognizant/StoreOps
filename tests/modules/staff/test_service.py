"""Staff service tests -- token resolution is the auth backbone every other
module's "authenticated user" tests depend on."""

from __future__ import annotations

import pytest

from app.core.errors import UnauthorizedError
from app.modules.staff.service import staff_service


def test_get_user_by_token_resolves_seeded_demo_user() -> None:
    user = staff_service.get_user_by_token("demo-store-manager-token")

    assert user.id == "user-store-manager"


def test_get_user_by_token_rejects_unknown_token() -> None:
    with pytest.raises(UnauthorizedError):
        staff_service.get_user_by_token("not-a-real-token")


def test_list_users_filters_by_store() -> None:
    users = staff_service.list_users(store_id="store-1")

    assert all(u.store_id == "store-1" for u in users)
    assert len(users) >= 3


def test_get_user_or_none_returns_none_for_unknown_id() -> None:
    assert staff_service.get_user_or_none("ghost") is None
