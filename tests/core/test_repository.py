"""Unit tests for the generic in-memory repository base."""

from __future__ import annotations

import pytest

from app.core.errors import NotFoundError
from app.core.repository import InMemoryRepository


def test_add_without_explicit_id_generates_one() -> None:
    repo = InMemoryRepository[str]()

    new_id = repo.add("hello")

    assert repo.get(new_id) == "hello"


def test_add_with_explicit_id_uses_it() -> None:
    repo = InMemoryRepository[str]()

    repo.add("hello", item_id="fixed-id")

    assert repo.get("fixed-id") == "hello"


def test_get_missing_raises_not_found_error() -> None:
    repo = InMemoryRepository[str](not_found_message="nope")

    with pytest.raises(NotFoundError):
        repo.get("missing")


def test_get_or_none_returns_none_for_missing() -> None:
    repo = InMemoryRepository[str]()

    assert repo.get_or_none("missing") is None


def test_set_updates_existing_item() -> None:
    repo = InMemoryRepository[str]()
    repo.add("v1", item_id="x")

    repo.set("x", "v2")

    assert repo.get("x") == "v2"


def test_set_on_missing_item_raises_not_found_error() -> None:
    repo = InMemoryRepository[str]()

    with pytest.raises(NotFoundError):
        repo.set("missing", "v2")


def test_delete_removes_item() -> None:
    repo = InMemoryRepository[str]()
    repo.add("v1", item_id="x")

    repo.delete("x")

    with pytest.raises(NotFoundError):
        repo.get("x")


def test_delete_missing_raises_not_found_error() -> None:
    repo = InMemoryRepository[str]()

    with pytest.raises(NotFoundError):
        repo.delete("missing")


def test_clear_empties_the_store() -> None:
    repo = InMemoryRepository[str]()
    repo.add("v1", item_id="x")

    repo.clear()

    assert repo.list_all() == []
