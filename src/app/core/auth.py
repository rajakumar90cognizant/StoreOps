"""Minimal fake bearer-token auth for the StoreOps demo.

There is no real identity provider here -- `staff.repository` seeds a
handful of demo users and tokens at import time. This module resolves the
`Authorization: Bearer <token>` header against that table via
`staff_service` (never the staff repository directly). Every route that
needs "the authenticated user/store" depends on `get_current_user`.

Uses FastAPI's `HTTPBearer` security scheme rather than a bare `Header()`
parameter so the OpenAPI docs expose a real "Authorize" padlock (global,
plus per-endpoint) that Swagger UI actually threads through into
requests -- a plain `Header()` param renders as ordinary free text and is
easy to fill in without it ever reaching the request. `auto_error=False`
is required: the default `HTTPBearer` raises its own `HTTPException` on a
missing/malformed header, which would violate this project's "no raw
HTTPException in routes/services" rule -- we catch that case ourselves
and raise `UnauthorizedError` instead.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import UnauthorizedError
from app.modules.staff.models import User
from app.modules.staff.service import staff_service

_bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste one of the seeded demo tokens, e.g. demo-store-manager-token "
    "(see app-context skill / staff/repository.py for the full list).",
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing or malformed Authorization header")
    return staff_service.get_user_by_token(credentials.credentials)
