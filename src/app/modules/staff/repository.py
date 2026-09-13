"""In-memory staff repository, seeded with demo users and tokens.

`staff` is the one module every other module reads from -- but always
through `staff_service` (see service.py), never this repository directly.
That indirection is the module-boundary rule this whole harness exists to
enforce.
"""

from __future__ import annotations

from app.core.repository import InMemoryRepository
from app.modules.staff.models import AuthToken, StaffRole, User


class StaffRepository:
    def __init__(self) -> None:
        self._users = InMemoryRepository[User](not_found_message="Staff member not found")
        self._tokens_by_value: dict[str, AuthToken] = {}
        self._seed_demo_data()

    def add_user(self, user: User) -> str:
        return self._users.add(user, item_id=user.id)

    def get_user(self, user_id: str) -> User:
        return self._users.get(user_id)

    def get_user_or_none(self, user_id: str) -> User | None:
        return self._users.get_or_none(user_id)

    def list_users(self, *, store_id: str | None = None) -> list[User]:
        users = self._users.list_all()
        if store_id is not None:
            users = [u for u in users if u.store_id == store_id]
        return users

    def register_token(self, token: AuthToken) -> None:
        self._tokens_by_value[token.token] = token

    def get_token(self, token_value: str) -> AuthToken | None:
        return self._tokens_by_value.get(token_value)

    def _seed_demo_data(self) -> None:
        demo_users = [
            User(
                id="user-store-manager",
                store_id="store-1",
                name="Priya Shah",
                email="priya.shah@storeops.example",
                staff_role=StaffRole.STORE_MANAGER,
            ),
            User(
                id="user-dept-lead",
                store_id="store-1",
                name="Marcus Webb",
                email="marcus.webb@storeops.example",
                staff_role=StaffRole.DEPARTMENT_LEAD,
            ),
            User(
                id="user-associate",
                store_id="store-1",
                name="Jamie Ortiz",
                email="jamie.ortiz@storeops.example",
                staff_role=StaffRole.ASSOCIATE,
            ),
        ]
        for user in demo_users:
            self.add_user(user)
        for token_value, user_id in (
            ("demo-store-manager-token", "user-store-manager"),
            ("demo-dept-lead-token", "user-dept-lead"),
            ("demo-associate-token", "user-associate"),
        ):
            self.register_token(AuthToken(token=token_value, user_id=user_id))


staff_repository = StaffRepository()
