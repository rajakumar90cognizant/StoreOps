# Generator Summary -- Sprint 2: Alerts shift-handover audit entries

This is a first attempt for Sprint 2 -- the `evaluator-feedback.md` found
in `.harness/output/` at invocation time was Sprint 1's (already archived
to `.harness/reviews/sprint-1-evaluator-feedback.md`), not a Sprint 2
retry marker, so there is no "Fixing from prior FAIL" section.

## IMPORTANT: verification commands could not be executed

The tool set available in this session did **not** include a Bash/shell
tool (only Read, Write, Edit, Grep, Glob were available -- same
constraint Sprint 1's generator and Sprint 1's evaluator both hit and
documented). I could not run:

```
mypy . && ruff check . && pytest --cov=src/app --cov-report=json --cov-report=term-missing && python scripts/check_coverage.py
```

and cannot paste real output. Instead I did the following static
verification using Grep across the whole `src/app` tree, and manual
review against `pyproject.toml`'s exact configs:

- **Module boundary (`from app.modules.<other>.repository import`)**:
  grepped `src/app/modules` for that pattern -- every hit is a module
  importing *only its own* repository (`activities` -> its own repo,
  `staff` -> its own, `programmes` -> its own, `reports` -> its own,
  `alerts` -> its own). No cross-module repository import anywhere,
  including in the two files this sprint touched.
- **No raw exceptions**: grepped `src/app` for
  `raise (Exception|HTTPException)\(` -- the only hit is the docstring
  in `app/core/errors.py` describing the rule itself, not a real raise.
  This sprint added zero new `raise` statements of any kind (the handler
  has no error path per the contract's own note that sprint 1's payload
  contract guarantees all keys are present).
- **Event bus wiring**: grepped `src/app` for `event_bus\.(emit|subscribe)`
  -- confirms exactly one new line, `main.py:30`
  (`event_bus.subscribe(BULK_STATUS_UPDATED_EVENT,
  alert_service.handle_activity_bulk_status_updated)`), alongside the
  pre-existing `MEMBER_ADDED_EVENT` subscription and the two emit sites
  (`activities/service.py:108`, `programmes/service.py:77`) -- no new
  emit added, matching the contract's subscribe-only scope.
- **No `alerts` import in `activities`**: grepped
  `src/app/modules/activities` for `import alerts` -- zero matches.
  `alerts/service.py` also imports nothing from
  `app.modules.activities.*` (confirmed by direct read of the full file
  -- its only imports are `app.core.event_bus.Event`,
  `app.modules.alerts.models`, `app.modules.alerts.repository`).
- **Type annotations / line length**: every new/changed line manually
  checked against `mypy --strict` requirements (full param + return
  annotations on `handle_activity_bulk_status_updated` and the new test
  helper `_bulk_status_updated_event`) and against ruff's `line-length =
  100` (longest new line, `main.py:30`, is 97 characters).
- **Import ordering**: the one new import in `main.py`
  (`from app.modules.activities.service import BULK_STATUS_UPDATED_EVENT`)
  sits alphabetically between `activities.routes` and `alerts.routes`,
  matching isort's first-party-sorted convention already used in that
  file.

I am flagging this plainly as a known gap below rather than asserting a
false PASS -- the Evaluator or a human must actually run the gate
commands before this is merged.

## Self-check table

| AC | Description | Satisfied at |
|---|---|---|
| 1 | Single `activity.bulk_status_updated` event handled directly -> exactly one new `SHIFT_HANDOVER` notification for the owner, `source_module == "activities"` | `src/app/modules/alerts/service.py:57-70` (`handle_activity_bulk_status_updated`); verified by `tests/modules/alerts/test_service.py::test_handle_activity_bulk_status_updated_creates_one_shift_handover_notification` |
| 2 | Two events, different `task_id`s, same `owner_id` -> exactly two `SHIFT_HANDOVER` notifications, each message referencing a different task id | `src/app/modules/alerts/service.py:63-69` (message built as `f"Task '{task_id}' status changed to '{new_status}'."`, one call per event -- no dedup/merge); verified by `tests/modules/alerts/test_service.py::test_handle_activity_bulk_status_updated_creates_one_audit_entry_per_task` |
| 3 | Full path via `app.main` wiring + `activity_service.bulk_update_status` -> a new `SHIFT_HANDOVER` notification whose message includes the task id, with `activities/service.py` never importing `alerts.service` | `src/app/main.py:17,30` (`BULK_STATUS_UPDATED_EVENT` import + `event_bus.subscribe(...)` at module import time); verified by `tests/modules/alerts/test_service.py::test_bulk_update_status_end_to_end_fires_shift_handover_notification`, which only ever calls `activity_service` and `alert_service` -- it never wires them together itself, so the coupling under test is exclusively `app.main`'s |
| 4 | Batch with one real task + one nonexistent task id -> exactly one new `SHIFT_HANDOVER` notification (for the real task only), none referencing the nonexistent id | `src/app/modules/activities/service.py:91-119` (unchanged from Sprint 1 -- `event_bus.emit(...)` only runs inside the per-item success branch, never for a caught `NotFoundError`) + `alerts/service.py:57-70`; verified by `tests/modules/alerts/test_service.py::test_bulk_update_status_end_to_end_skips_notification_for_failed_item`, which asserts `result.failures[0].task_id == "ghost-task"`, exactly one matching notification, and `not any("ghost-task" in n.message for n in notifications)` |

## Files changed

| File | Reason |
|---|---|
| `src/app/modules/alerts/service.py` | Added `AlertService.handle_activity_bulk_status_updated(self, event: Event) -> None`, the new EventBus subscriber that creates a `SHIFT_HANDOVER` notification for `event.payload["owner_id"]` only, reusing the existing `create_notification` helper; reads only `event.payload`, imports nothing from `activities` |
| `src/app/main.py` | Imported `BULK_STATUS_UPDATED_EVENT` from `app.modules.activities.service` and added `event_bus.subscribe(BULK_STATUS_UPDATED_EVENT, alert_service.handle_activity_bulk_status_updated)` alongside the existing `MEMBER_ADDED_EVENT` subscription; updated the file's module docstring to mention `activities` events, not just `programmes` |
| `tests/modules/alerts/test_service.py` | Added a module-level `Event` import (removed a now-redundant local import in the pre-existing `test_handle_programme_member_added_...` test), a `_bulk_status_updated_event` helper matching AC1's exact payload shape, and four new tests covering AC1 (single event), AC2 (two events/same owner -> two distinct-message notifications), AC3 (full `activities` -> event_bus -> `alerts` path via `app.main`'s real wiring), and AC4 (partial-failure batch skips the failed item) |

## Design notes / decisions

- The notification message format (`"Task '{task_id}' status changed to
  '{new_status}'."`) was chosen to satisfy AC2's requirement that each
  notification's message reference its own distinct task id, and AC3/AC4's
  requirement that the message "includes that task's id" -- both are
  satisfied by the same f-string, no per-AC special-casing needed.
- `handle_activity_bulk_status_updated` deliberately ignores
  `event.payload["assignee_id"]` entirely (per the contract's non-goals --
  only `owner_id` is notified), and ignores `previous_status`/`actor_id`
  (not needed for the audit-entry message the contract specifies).
- No new `AppError` subclass or `try/except` was added to the handler:
  per the contract's own constraint, Sprint 1's `bulk_update_status`
  payload always carries all seven keys for a successfully-emitted event,
  so there is no malformed-payload path to guard against without
  fabricating an untestable branch.
- Kept the two "end-to-end" tests as plain synchronous `def ... -> None`
  functions (not `async def`) since neither awaits anything --
  `activity_service.bulk_update_status` and `alert_service.list_for_user`
  are both synchronous; only `httpx.AsyncClient`-based route tests need
  `async def` per `how-to-test`.
- The local `import app.main` inside the two end-to-end tests is
  intentionally explicit (even though `tests/conftest.py` already imports
  `app.main` once at collection time, which is what actually registers
  the subscription for the whole test session) -- it documents, at the
  point of use, exactly which import is responsible for the coupling
  under test, matching the contract's phrasing "once `app.main` has run
  its module-level wiring."

## Known gaps

1. **Verification commands not run** (see banner above) -- `mypy .`,
   `ruff check .`, `pytest --cov=...`, and `scripts/check_coverage.py`
   were not executed because no shell/Bash tool was available in this
   session. Static Grep-based checks (module boundary, raw-exception,
   event-bus-usage, cross-module import) all came back clean, as detailed
   above, but this is not a substitute for the real mypy/ruff/pytest/
   coverage run the contract requires. A developer or the Evaluator must
   run the four gate commands and report real output before this sprint
   can be marked PASS, per the precedent set by Sprint 1's evaluator
   feedback.
2. Coverage thresholds (service >= 80%, route >= 70%, overall >= 70%)
   were not measured for the same reason. This sprint added no new
   `routes.py` code at all (constraint: `alerts` has no public routes
   surface, and this sprint doesn't touch `activities/routes.py`), and
   the one new service method has full branch coverage across the 4 new
   tests, but the real coverage numbers are unverified.
3. Per the contract's own non-goals: no change to `GET /api/alerts`, no
   mark-as-read endpoint, no new `NotificationType`, no notification to
   `assignee_id`, no `reports`-side rollup -- all intentionally out of
   scope and untouched.
4. `src/app/modules/activities/*` was not modified in this sprint (per
   the contract's explicit constraint) -- confirmed by not touching any
   file under that path in this diff.
