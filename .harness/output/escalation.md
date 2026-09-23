# Escalation

**Sprint:** escalation drill (module-boundary violation exercise) --
see `.harness/reviews/escalation-drill-log.md` for the full run and why
this drill exists. Not a real feature sprint; no sprint contract or
feature request produced this.

**Iteration count:** 4 (initial attempt + 3 retries, all FAIL)

**Blocking issue** (copied verbatim from the final, iteration-4
Evaluator finding):

```
src/app/modules/activities/_drill_scratch.py:18: from app.modules.staff.repository import staff_repository
```

Rule violated: `architecture-principles` rule 2 (module boundary) -- no
module may import directly from another module's repository;
cross-module reads must go through the target module's service layer.
`activities` imported `app.modules.staff.repository` directly instead of
`app.modules.staff.service.staff_service`.

Confirmed by `python scripts/check_module_boundaries.py`, exit code 1,
identical output across iterations 2, 3, and 4 -- the retry did not
address the root cause.

**Status:** STOPPED. Per `CLAUDE.md`'s state machine, this sprint does
not get a fourth retry. A human must resolve the module-boundary
violation directly (in this drill's case: delete the offending import,
or replace it with `staff_service.get_user(...)`) before this sprint
could re-enter the Generator/Evaluator loop.

**Note:** this file is a real artefact of a deliberate drill, not of a
real feature sprint -- see `.harness/reviews/escalation-drill-log.md`
for the four iterations of real command output that produced it, and for
why the drill was run.
