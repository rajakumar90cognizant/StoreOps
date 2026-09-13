"""Unit tests for the AppError hierarchy."""

from __future__ import annotations

from app.core.errors import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


def test_app_error_carries_message_and_details() -> None:
    err = AppError("boom", details={"a": 1})

    assert err.message == "boom"
    assert err.details == {"a": 1}
    assert err.code == "APP_ERROR"
    assert err.status_code == 500


def test_details_defaults_to_empty_dict() -> None:
    assert AppError("x").details == {}


def test_not_found_error_has_404_and_code() -> None:
    err = NotFoundError("missing")

    assert err.status_code == 404
    assert err.code == "NOT_FOUND"


def test_validation_error_has_422_and_code() -> None:
    err = ValidationError("bad")

    assert err.status_code == 422
    assert err.code == "VALIDATION_ERROR"


def test_conflict_error_has_409_and_code() -> None:
    err = ConflictError("dup")

    assert err.status_code == 409
    assert err.code == "CONFLICT"


def test_forbidden_error_has_403_and_code() -> None:
    err = ForbiddenError("nope")

    assert err.status_code == 403
    assert err.code == "FORBIDDEN"


def test_unauthorized_error_has_401_and_code() -> None:
    err = UnauthorizedError("who are you")

    assert err.status_code == 401
    assert err.code == "UNAUTHORIZED"
