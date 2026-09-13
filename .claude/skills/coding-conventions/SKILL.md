---
name: coding-conventions
description: The actual Python/FastAPI/Pydantic v2 idioms used across the StoreOps baseline -- the Generator must match these exactly, not generic Python style.
---

# StoreOps coding conventions

These are drawn from the generated baseline (`src/app/`), not generic
PEP 8. Match them exactly -- a Generator diff that introduces a different
idiom for something already established elsewhere is a review finding
even if it's individually reasonable Python.

## File header

Every module file starts:

```python
"""One-line purpose, plus 2-4 lines of *why*, not what -- see any existing
file in src/app/ for the tone."""

from __future__ import annotations
```

## Enums

Domain enums are `StrEnum` (stdlib, Python 3.11+), values equal to their
names, e.g.:

```python
class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
```

Not `Enum` + `auto()`, not plain string literals typed as `Literal[...]`.

## Models

Pydantic v2 `BaseModel`, three kinds per module as needed:

- The stored domain entity (e.g. `Task`, `Project`, `Notification`) --
  always has `id: str` and, where relevant, `store_id: str`.
- `*Create` / `*Update` request bodies -- only the fields a client may
  set. `*Update` models make every field `X | None = None` so
  `model_dump(exclude_unset=True)` produces exactly the intended partial
  update (see `activities/service.py::update_activity`).
- `*Out` response models with a `from_<entity>` classmethod:
  `cls(**entity.model_dump())`. Routes return `*Out`, never the internal
  entity model directly.

Mutable-default fields use `Field(default_factory=list)` /
`Field(default_factory=dict)`, never a bare `= []` / `= {}` default.

## IDs and timestamps

IDs: `uuid4().hex`. Timestamps: `datetime.now(UTC)` (stdlib `UTC`
constant, Python 3.11+) -- never naive `datetime.now()`, never
`datetime.utcnow()` (deprecated).

## Module-level singletons

Each `repository.py` and `service.py` ends with one module-level
instance, lowercase-with-underscores, matching the class:

```python
activity_repository = ActivityRepository()
```

```python
activity_service = ActivityService()
```

Other modules import the singleton (`from app.modules.staff.service
import staff_service`), never the class, and never construct their own
second instance.

## Partial updates

Use `model.model_copy(update={...})`, not manual field-by-field mutation
(pydantic models here are effectively immutable value objects once
constructed). Always fold `"updated_at": datetime.now(UTC)` into the same
`update` dict.

## Dependency injection

FastAPI `Depends(get_current_user)` / `Query(default=..., alias=...)` as
argument defaults is intentional and required -- do not "fix" a linter
warning about calling a function in a default argument for these; see
`pyproject.toml`'s `ruff.lint.ignore = ["B008"]`.

## Typing and tooling

- `mypy --strict` (via `mypy .`, configured in `pyproject.toml`) must show
  zero errors. Annotate every function signature, including test
  functions (`-> None`).
- `ruff check .` must show zero errors. Line length 100.
- `src/` layout with a Hatchling `[tool.hatch.build.targets.wheel]
  packages = ["src/app"]` so the installed/import name is `app`, matching
  `uvicorn app.main:app`.

## Test conventions

- One `_reset_state` autouse fixture in `tests/conftest.py` clears every
  module's in-memory repository except `staff_repository` before each
  test -- write new tests assuming a clean slate, and never assert a
  literal count of items unless you created every one of them in that
  test.
- Async route tests are plain `async def test_...() -> None:` -- no
  `@pytest.mark.asyncio` needed (`asyncio_mode = "auto"`).
