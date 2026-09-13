"""Unit tests for the in-memory EventBus."""

from __future__ import annotations

from app.core.event_bus import Event, EventBus


def test_emit_calls_subscribed_handler_with_payload() -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []
    bus.subscribe("thing.happened", lambda event: received.append(event.payload))

    bus.emit("thing.happened", {"id": "123"})

    assert received == [{"id": "123"}]


def test_emit_with_no_subscribers_does_nothing() -> None:
    bus = EventBus()

    bus.emit("nobody.listening", {"x": 1})  # must not raise


def test_multiple_handlers_all_run_in_order() -> None:
    bus = EventBus()
    calls: list[str] = []
    bus.subscribe("e", lambda _: calls.append("first"))
    bus.subscribe("e", lambda _: calls.append("second"))

    bus.emit("e")

    assert calls == ["first", "second"]


def test_emit_without_payload_defaults_to_empty_dict() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("e", received.append)

    bus.emit("e")

    assert received[0].payload == {}
