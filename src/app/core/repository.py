"""Generic thread-safe in-memory repository base.

Each module's own `repository.py` wraps an instance of this. It is shared
infrastructure, not a module boundary: importing `InMemoryRepository` from
another module's code is fine. Importing a *concrete module repository*
(e.g. `app.modules.activities.repository`) from outside that module is the
violation this project's architecture forbids -- cross-module reads must
go through the target module's service layer instead.
"""

from __future__ import annotations

import threading
from typing import Generic, TypeVar
from uuid import uuid4

from app.core.errors import NotFoundError

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    """Dict-backed store guarded by a lock, keyed by a generated or given id."""

    def __init__(self, *, not_found_message: str = "Resource not found") -> None:
        self._items: dict[str, T] = {}
        self._lock = threading.Lock()
        self._not_found_message = not_found_message

    def add(self, item: T, *, item_id: str | None = None) -> str:
        new_id = item_id or uuid4().hex
        with self._lock:
            self._items[new_id] = item
        return new_id

    def get(self, item_id: str) -> T:
        with self._lock:
            item = self._items.get(item_id)
        if item is None:
            raise NotFoundError(self._not_found_message, details={"id": item_id})
        return item

    def get_or_none(self, item_id: str) -> T | None:
        with self._lock:
            return self._items.get(item_id)

    def list_all(self) -> list[T]:
        with self._lock:
            return list(self._items.values())

    def set(self, item_id: str, item: T) -> None:
        with self._lock:
            if item_id not in self._items:
                raise NotFoundError(self._not_found_message, details={"id": item_id})
            self._items[item_id] = item

    def delete(self, item_id: str) -> None:
        with self._lock:
            if item_id not in self._items:
                raise NotFoundError(self._not_found_message, details={"id": item_id})
            del self._items[item_id]

    def clear(self) -> None:
        """Reset to empty. Used by test fixtures for isolation between tests."""
        with self._lock:
            self._items.clear()
