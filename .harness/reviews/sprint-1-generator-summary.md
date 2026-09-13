# Generator Summary -- Sprint 1: Activities bulk status update

This is a first attempt (no `evaluator-feedback.md` existed for sprint 1
at invocation time), so there is no "Fixing from prior FAIL" section.

## IMPORTANT: verification commands could not be executed

The tool set available in this session did **not** include a Bash/shell
tool (only Read, Write, Edit, Grep, Glob were available). I could not run:

```
mypy . && ruff check . && pytest --cov=src/app --cov-report=json --cov-report=term-missing && python scripts/check_coverage.py
```

and cannot paste real output as the contract requires. Instead I did a
careful manual static review against `pyproject.toml`'s exact configs
(mypy --strict, ruff line-length 100, ruff import-order/isort rules,
`asyncio_mode = auto`) -- checked import ordering alphabetically in every
edited file, checked every new/changed line's length is under 100 chars,
checked every new function has full type annotations, checked the one
`ValidationError(details=...)` call only ever carries JSON-serialisable
values, and traced every new type through `Task.model_copy`, `TaskOut`,
and the event payload for type compatibility with mypy strict mode. I am
flagging this plainly as a known gap below rather than asserting a false
PASS -- the Evaluator or a human must actually run the gate commands
before this is merged.

## Self-check table

| AC | Description | Satisfied at |
|---|---|---|
| 1 | Partial failure: 2 tasks updated, 1 `NOT_FOUND` failure, no `AppError` raised for the batch call | `src/app/modules/activities/service.py:81-123` (`bulk_update_status`, per-item try/except around `self._repository.get`); verified by `tests/modules/activities/test_service.py::test_bulk_update_status_partial_failure_updates_valid_tasks_and_reports_ghost` (lines 104-125) |
| 2 | Event payload has exact keys `task_id`, `previous_status`, `new_status`, `owner_id`, `actor_id` for one successful update | `src/app/modules/activities/service.py:108-119` (`event_bus.emit(BULK_STATUS_UPDATED_EVENT, {...})`); verified by `tests/modules/activities/test_service.py::test_bulk_update_status_emits_one_event_per_successful_update` (lines 128-149), which subscribes before the call per `tests/core/test_event_bus.py`'s pattern |
| 3 | Empty `updates` raises `ValidationError`, zero events captured | `src/app/modules/activities/service.py:84-88` (`if not payload.updates: raise ValidationError(...)`); verified by `tests/modules/activities/test_service.py::test_bulk_update_status_rejects_empty_updates_with_no_side_effects` (lines 152-161) |
| 4 | Invalid status value (`"TODO"`) rejected over HTTP with 422, task state unchanged on re-fetch | `src/app/modules/activities/models.py:92-96` (`BulkStatusUpdateItem.status: Literal[TaskStatus.DONE, TaskStatus.BLOCKED]` -- FastAPI/Pydantic reject any other value at the request-validation layer, before the route body even runs); verified by `tests/modules/activities/test_routes.py::test_bulk_update_status_rejects_invalid_status_value_and_leaves_task_unchanged` (lines 96-113) |
| 5 | Two `TODO` tasks bulk-set to `DONE` over HTTP by a store manager: `updated` has both ids/status, `failures` empty, re-fetch confirms | `src/app/modules/activities/routes.py:42-46` (`bulk_update_status` route, single call into the service) + `service.py:81-123`; verified by `tests/modules/activities/test_routes.py::test_bulk_update_status_succeeds_for_both_tasks` (lines 116-148) |

## Files changed

| File | Reason |
|---|---|
| `src/app/modules/activities/models.py` | Added `BulkStatusUpdateItem`, `BulkStatusUpdateRequest`, `BulkStatusFailure`, `BulkStatusUpdateResponse` per contract's exact field shapes |
| `src/app/modules/activities/service.py` | Added `BULK_STATUS_UPDATED_EVENT` constant and `ActivityService.bulk_update_status`: validates non-empty `updates`, loops per item (get-or-record-`NOT_FOUND`-failure, else update + emit event), returns typed response; no cross-module writes, no raw exceptions |
| `src/app/modules/activities/routes.py` | Added `PATCH /api/activities/bulk-status`, registered before the existing `PATCH /api/activities/{task_id}` (per the contract's routing-order constraint) so FastAPI doesn't swallow `"bulk-status"` as a `task_id` path param; route calls the service exactly once and does no per-item looping itself |
| `tests/modules/activities/test_service.py` | Added 3 new tests covering AC1 (partial failure + state), AC2 (event payload shape via test-subscribed handler), AC3 (empty-list `ValidationError` + zero side effects) |
| `tests/modules/activities/test_routes.py` | Added 2 new tests covering AC4 (422 on invalid literal + unchanged state on re-fetch) and AC5 (successful two-task batch + independent re-fetch confirmation) |

## Design notes / decisions

- `bulk_update_status` returns `BulkStatusUpdateResponse` (containing
  `TaskOut` instances) directly from the service, matching the contract's
  literal signature (`-> BulkStatusUpdateResponse`) even though this
  slightly departs from the usual "service returns domain entities, route
  converts to `*Out`" convention elsewhere in this module -- the contract
  specifies the service's own return type as the response model itself,
  so `TaskOut.from_task(...)` is called inside `bulk_update_status`.
- `BulkStatusFailure.code`/`message` are populated straight from the
  caught `NotFoundError`'s own `.code` ("NOT_FOUND") and `.message`
  attributes rather than a hand-written string, so they stay in sync with
  `app/core/errors.py` automatically.
- Event is emitted once per successfully-updated task only, inside the
  per-item loop, immediately after that item's `repository.update(...)`
  call and before moving to the next item -- never batched, never emitted
  for a `NOT_FOUND` item, matching the constraint.
- No import of `app.modules.alerts.*` anywhere in this diff (grepped
  manually across all three changed source files).

## Known gaps

1. **Verification commands not run** (see banner above) -- `mypy .`,
   `ruff check .`, `pytest --cov=...`, and `scripts/check_coverage.py`
   were not executed because no shell/Bash tool was available in this
   session. All checks below are from manual static review only:
   - Import ordering in every edited file matches isort's alphabetical
     first-party-last convention already used in the codebase.
   - No line in any edited file exceeds 100 characters (longest new
     lines manually counted, all <= ~97 chars).
   - Every new function/method has full parameter and return
     annotations (required for `mypy --strict`).
   - The one new `ValidationError(..., details={"updates": payload.updates})`
     call only fires when `payload.updates == []`, so the `details` dict
     is always JSON-serialisable (`{"updates": []}`) through
     `app/main.py`'s `JSONResponse` -- it is never populated with
     unserialisable Pydantic model instances.
   - `Literal[TaskStatus.DONE, TaskStatus.BLOCKED]` relies on Pydantic
     v2's documented behaviour of treating an all-same-enum `Literal` as
     an enum-restricted schema (accepts/rejects by value, same as the
     enum's `.value` strings). This is not unit-tested against Pydantic's
     internals directly, only indirectly via
     `test_bulk_update_status_rejects_invalid_status_value_and_leaves_task_unchanged`.
     If the Evaluator's actual `pytest` run shows this literal typing
     does not reject `"TODO"` as expected, the fallback fix is to add an
     explicit `field_validator` on `BulkStatusUpdateItem.status` instead
     of relying on the bare `Literal` annotation.
2. Coverage thresholds (service >= 80%, route >= 70%, overall >= 70%)
   were not measured for the same reason -- the new code paths are
   exercised by the 5 new tests (both the success and every failure
   branch of `bulk_update_status`, plus both branches of the route), so
   coverage should be high, but this is not a substitute for the actual
   `coverage.json` numbers.
3. Per the contract's own non-goals: no `alerts` subscriber, no role/
   ownership restriction on who may call `bulk-status`, no dedup of
   repeated `task_id`s within one request -- all intentionally deferred,
   matching the sprint contract's stated scope.
