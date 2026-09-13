"""In-memory typed event bus.

Cross-module side effects -- a write in one module causing behaviour in
another -- must go through `EventBus.emit(...)` and a subscriber wired up
in `app.main`, never a direct service-to-service import for a *write*.
Reads across modules go through the target module's service directly
(that's allowed); only write-triggered side effects are required to use
this bus. This is the mechanism, e.g., that lets `programmes.add_member`
cause `alerts` to create a Notification without importing
`app.modules.alerts.service`.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True)
class Event:
    """A single event raised on the bus."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Synchronous in-memory publish/subscribe bus.

    One process, one shared instance (`event_bus` below). Handlers run
    inline, inside the emitting call, so a subscriber raising an AppError
    propagates back to the original caller exactly like a direct call
    would -- there is no hidden async fan-out to reason about.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            self._handlers[event_name].append(handler)

    def emit(self, event_name: str, payload: dict[str, Any] | None = None) -> None:
        event = Event(name=event_name, payload=payload or {})
        with self._lock:
            handlers = list(self._handlers.get(event_name, ()))
        for handler in handlers:
            handler(event)


event_bus = EventBus()
