"""Staff service -- the only sanctioned way for other modules to read staff data."""

from __future__ import annotations

from app.core.errors import NotFoundError, UnauthorizedError
from app.modules.staff.models import User
from app.modules.staff.repository import staff_repository


class StaffService:
    def __init__(self) -> None:
        self._repository = staff_repository

    def get_user(self, user_id: str) -> User:
        return self._repository.get_user(user_id)

    def get_user_or_none(self, user_id: str) -> User | None:
        return self._repository.get_user_or_none(user_id)

    def list_users(self, *, store_id: str | None = None) -> list[User]:
        return self._repository.list_users(store_id=store_id)

    def get_user_by_token(self, token_value: str) -> User:
        token = self._repository.get_token(token_value)
        if token is None:
            raise UnauthorizedError("Invalid or expired token")
        try:
            return self._repository.get_user(token.user_id)
        except NotFoundError as exc:
            raise UnauthorizedError("Token refers to an unknown user") from exc


staff_service = StaffService()
