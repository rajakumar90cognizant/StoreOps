---
name: architecture-principles
description: The five non-negotiable StoreOps architecture rules -- layering, module boundary, event-bus-only writes, the AppError contract, and read-only reports. Every Generator and Evaluator invocation reads this.
---

# StoreOps architecture principles

These five rules exist because a prior AI-coding experiment on this
project produced four concrete failure modes (direct cross-module repo
imports, raw exception throws, status-code-only tests, missing event-bus
integration). Every rule below maps to preventing one of those.

## 1. Layering: Routes -> Service -> Repository, never skipped

Each module's `routes.py` only validates input (via Pydantic models) and
shapes output -- it calls exactly one service method per endpoint and
never touches a repository or another module's anything directly.
`service.py` holds all business logic and is the only thing that touches
`repository.py`. `repository.py` is a dumb in-memory store: it has no
knowledge of HTTP, no knowledge of other modules, and never calls an
external service.

**What breaks without it:** business logic ends up scattered across route
handlers, making it untestable without spinning up the ASGI app, and
repositories start accumulating cross-cutting concerns that make the
in-memory store impossible to swap for a real database later.

## 2. Module boundary: no cross-module repository imports

No module may `from app.modules.<other>.repository import ...`.
Cross-module *reads* go through the target module's service only, e.g.
`app/modules/activities/service.py` imports `staff_service` from
`app.modules.staff.service`, never `staff_repository` from
`app.modules.staff.repository`.

**What breaks without it:** any module can reach into any other module's
internal storage representation, so changing `activities`' in-memory
schema silently breaks `reports` with no compiler error -- the whole point
of a service layer (a stable contract) is defeated.

## 3. Event bus only for cross-module writes

A **write** in one module that needs to cause a side effect in another
module must go through `event_bus.emit(event_name, payload)` (see
`component-patterns` for the exact shape), never a direct import of the
other module's service to perform that write. The one example in the
baseline: `programmes.service.add_member` emits `programme.member_added`;
`alerts.service.handle_programme_member_added` is subscribed to it in
`app/main.py`. `programmes/service.py` does not, and must never, import
`app.modules.alerts.service`.

**What breaks without it:** modules become tightly coupled at the write
path -- `programmes` can't be deployed, tested, or reasoned about without
also loading `alerts`' internals, and every new side effect means editing
someone else's service file instead of just subscribing to an event.

## 4. The AppError contract

Zero `raise Exception(...)` and zero `raise HTTPException(...)` anywhere
in a `service.py` or `routes.py`. Every intentional error is one of the
`AppError` subclasses in `app/core/errors.py`:
`NotFoundError` (404), `ValidationError` (422), `ConflictError` (409),
`ForbiddenError` (403), `UnauthorizedError` (401). `app/main.py`'s single
`app_error_handler` converts any `AppError` into
`{"error": {"code", "message", "details"}}`.

**What breaks without it:** every raw exception is a different,
undocumented shape reaching the client, and there's no single place to
audit every error path a service can take -- which is exactly the failure
mode ("raw Error throws... bypassing the typed AppError hierarchy") the
capstone's client context calls out by name.

## 5. Read-only reports

`reports.service` may call `activities.service` and `programmes.service`
for read-only lookups (that's rule 2's allowed case), but it must never
write to another module's repository or service -- and it must never be
the *target* of another module's event-bus emit that expects a write back
into `activities` or `programmes`. `reports` only ever writes to its own
`report_repository`.

**What breaks without it:** aggregation logic starts mutating the data
it's supposed to be summarising, and a report becomes indistinguishable
from a side-effecting command -- callers can no longer safely generate a
report without risking a state change elsewhere.
