"""Typed error hierarchy for StoreOps.

Every service and route in this project raises one of these AppError
subclasses instead of a bare Exception or HTTPException. `app.main`
installs a single exception handler that turns any AppError into the JSON
envelope:

    {"error": {"code": ..., "message": ..., "details": ...}}

Zero raw `raise Exception(...)` or `raise HTTPException(...)` is allowed in
`app.modules.*.service` or `app.modules.*.routes` -- that is the failure
mode this hierarchy exists to eliminate.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for every error StoreOps raises on purpose.

    Attributes:
        code: a short machine-readable identifier, e.g. "NOT_FOUND".
        message: a human-readable description, safe to show to a client.
        status_code: the HTTP status this error maps to.
        details: optional structured context (offending id, field, ...).
    """

    code: str = "APP_ERROR"
    status_code: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class NotFoundError(AppError):
    """The requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404


class ValidationError(AppError):
    """The request payload is well-formed JSON but violates a business rule."""

    code = "VALIDATION_ERROR"
    status_code = 422


class ConflictError(AppError):
    """The request conflicts with the resource's current state."""

    code = "CONFLICT"
    status_code = 409


class ForbiddenError(AppError):
    """The caller is authenticated but not authorised for this action."""

    code = "FORBIDDEN"
    status_code = 403


class UnauthorizedError(AppError):
    """The caller could not be authenticated at all."""

    code = "UNAUTHORIZED"
    status_code = 401
