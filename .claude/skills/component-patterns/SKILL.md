---
name: component-patterns
description: The concrete EventBus.emit call shape, AppError subclass hierarchy, and in-memory-repository-with-locks pattern, taken directly from the StoreOps baseline. Copy these shapes, don't reinvent them.
---

# StoreOps component patterns

## EventBus.emit -- exact shape

Defined in `src/app/core/event_bus.py`. One shared instance:
`from app.core.event_bus import event_bus`.

To **emit** (always from a `service.py`, after the write that triggers it,
never before):

```python
event_bus.emit(
    MEMBER_ADDED_EVENT,          # a module-level str constant, not a magic string
    {                             # payload: dict[str, Any], JSON-serialisable values only
        "programme_id": programme_id,
        "programme_name": updated_project.name,
        "user_id": member_user.id,
        "role": payload.role.value,
    },
)
```

The event name is a module-level constant in the *emitting* module's
`service.py` (see `programmes/service.py`'s
`MEMBER_ADDED_EVENT = "programme.member_added"`), dot-namespaced as
`<module>.<past_tense_verb>`.

To **subscribe** (always in `app/main.py`, at import time, never inside a
route or another module's service):

```python
event_bus.subscribe(MEMBER_ADDED_EVENT, alert_service.handle_programme_member_added)
```

The handler lives in the *subscribing* module's `service.py` as a regular
method taking one `Event` argument:

```python
def handle_programme_member_added(self, event: Event) -> None:
    """Subscriber for `programme.member_added` (see app.main wiring)."""
    programme_name = event.payload["programme_name"]
    self.create_notification(
        user_id=event.payload["user_id"],
        notification_type=NotificationType.SHIFT_HANDOVER,
        message=f"You were added to programme '{programme_name}'.",
        source_module="programmes",
    )
```

Adding a new cross-module write side effect means: (1) a new constant +
`event_bus.emit(...)` call in the emitting service, (2) a new handler
method in the subscribing service, (3) one new
`event_bus.subscribe(...)` line in `app/main.py`. Nothing else changes.

## AppError hierarchy -- exact shape

Defined in `src/app/core/errors.py`. Base class carries `code: str`,
`status_code: int` (class attributes, overridden per subclass) and
`message: str`, `details: dict[str, Any]` (instance attributes):

```python
class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404
```

Raise with a message and, when there's a specific offending value, a
`details` dict for debuggability:

```python
raise ValidationError(
    "assignee_id does not refer to a known staff member",
    details={"assignee_id": assignee_id},
)
```

When translating a caught `AppError` into a different one (e.g. a
`NotFoundError` from a cross-module lookup becoming a `ValidationError` in
the caller, per `activities/service.py`'s `_require_valid_assignee`),
always `raise ... from exc` to preserve the chain.

`app/main.py`'s single handler is the only place that turns an `AppError`
into an HTTP response -- services and routes only ever *raise*, never
catch-and-format.

## In-memory repository with locks -- exact shape

`app/core/repository.py`'s `InMemoryRepository[T]` is the shared base
every module's own repository wraps (composition, not inheritance):

```python
class ActivityRepository:
    def __init__(self) -> None:
        self._store = InMemoryRepository[Task](not_found_message="Activity not found")

    def add(self, task: Task) -> str:
        return self._store.add(task, item_id=task.id)

    def get(self, task_id: str) -> Task:
        return self._store.get(task_id)
    ...
```

Every method on `InMemoryRepository` takes `self._lock` (a
`threading.Lock`) for the duration of the dict access and releases it
before returning -- never hold the lock across a call into another
service or across an `event_bus.emit`. `get()` raises `NotFoundError`
itself (with the message given at construction) rather than returning
`None`; use `get_or_none()` when a missing item is a valid, non-error
case. Every module repository also exposes a `clear()` passthrough (used
only by `tests/conftest.py`'s autouse fixture, never by application
code) -- except `staff_repository`, whose seeded demo users/tokens must
survive the whole test run.
