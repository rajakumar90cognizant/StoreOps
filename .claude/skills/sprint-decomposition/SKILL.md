---
name: sprint-decomposition
description: How to split a StoreOps feature request into 1-3 sprint contracts with testable GIVEN/WHEN/THEN acceptance criteria. Read by the planner subagent only.
---

# Sprint decomposition for StoreOps

## Drawing sprint boundaries

Split by **architectural seam, not by convenience**. A good seam in
StoreOps is one of:

- A single module's Routes -> Service -> Repository slice (e.g. "add
  bulk-status update to `activities`" is one sprint if it touches only
  `activities/*`).
- One cross-module event wiring (emit + subscribe), because that pair is
  independently testable at the service layer without the rest of the
  feature existing yet.
- One net-new endpoint versus one change to an existing endpoint's
  behaviour -- these have different blast radii and different test
  fixtures, so don't merge them into one contract just because they touch
  the same file.

A sprint that touches more than one module's `service.py` for a *write*
is almost always a sign the feature needs an event-bus wiring sprint of
its own -- split it out rather than letting the Generator improvise a
direct cross-module call.

## Writing acceptance criteria

Every AC is GIVEN/WHEN/THEN, and every AC must be answerable by pointing
at **one** of:

1. A specific state change readable back through an existing
   service/repository method or endpoint (not "the system updates
   correctly" -- name the field and the new value).
2. A specific `AppError` subclass and `code` raised for a specific bad
   input (not "invalid input is rejected" -- name the subclass).
3. A specific `event_bus.emit` call with a named event and the fields its
   payload must contain, plus what the subscriber is expected to do with
   them.

**Bad (rejected by the Evaluator, not testable as written):**
> GIVEN a bulk update request, WHEN it is submitted, THEN the activities
> are updated and the response is correct.

**Good (StoreOps-specific, one test assertion each):**
> GIVEN two existing tasks owned by the caller and one task ID that does
> not exist, WHEN `PATCH /api/activities/bulk-status` is called with
> `status: DONE` for all three IDs, THEN the two real tasks are updated to
> `DONE` (re-fetching each shows the new status), the response reports the
> missing ID as a per-item failure rather than aborting the whole request,
> and no `AppError` is raised for the batch as a whole.

> GIVEN a CRITICAL task past its due date, WHEN the SLA sweep runs, THEN
> exactly one `SLA_BREACH` notification is emitted via `event_bus.emit`
> with `payload["task_id"]` set, and the task's own `status` field is
> unchanged by the sweep.

## Non-goals

State explicitly what this sprint is *not* doing, especially anything the
feature request implies but that would require touching a module outside
this sprint's scope (e.g. "this sprint does not add a
`reports`-side rollup of bulk-updated tasks -- that would be a
`reports.service` change and belongs in a later sprint if requested").
Non-goals prevent the Generator from scope-creeping into another module's
files and prevent the Evaluator from failing the sprint for something it
was never asked to build.

## Contract template

```markdown
# Sprint N: <short title>

## Scope
- Module(s): <activities | programmes | staff | alerts | reports>
- Files: <exact paths under src/app/modules/.../ and tests/modules/.../>

## Acceptance Criteria
1. GIVEN ... WHEN ... THEN ...
2. GIVEN ... WHEN ... THEN ...

## Non-goals
- <explicitly deferred item> (see sprint N+1 / out of scope for this run)

## Constraints
- <any architecture-principles rule this sprint must respect that isn't
  obvious from the scope alone, e.g. "this must emit via event_bus, not
  call alerts.service directly">
```
