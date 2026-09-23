# Escalation drill log

**This is not a real sprint.** No feature request drove this. It exists
solely to answer a real gap identified in an architecture review of this
harness: `CLAUDE.md`'s escalation path (three retries, then
`.harness/output/escalation.md`) was fully specified but had never
actually fired during this repository's real demonstration run (both
`sprint-1` and `sprint-2` PASSed on the first attempt -- see
`.harness/reviews/sprint-1-run-log.md` and `sprint-2-run-log.md`). A path
that only exists on paper is unverified, so this drill exercises it with
real command output, then is removed.

## Setup

A throwaway file, `src/app/modules/activities/_drill_scratch.py`
(deleted after this drill; never part of any real sprint contract), was
used to generate four real Evaluator FAILs in a row against the actual
hard-gate commands in `how-to-review/SKILL.md` -- no output below is
invented; every result is a real `mypy`/`ruff`/
`check_module_boundaries.py`/grep run against real code in this
repository, captured at the time it ran.

## Iteration 1 -- raw exception (Dimension 1, architecture-principles rule 4)

Drill file content: a function raising `Exception("deliberate drill
violation: raw exception, iteration 1")`.

```
=== mypy . ===
Success: no issues found in 55 source files

=== ruff check . ===
All checks passed!

=== module boundary (AST) ===
OK: no cross-module repository imports

=== raw exception check ===
src/app/modules/activities/_drill_scratch.py:15:    raise Exception("deliberate drill violation: raw exception, iteration 1")
```

**Verdict: FAIL.** `grep -rn "raise Exception\|raise HTTPException"
src/app/modules/` found a match -- per `how-to-review`, "Any match is a
FAIL."

## Iteration 2 -- the "fix" trades one violation for another (Dimension 1, architecture-principles rule 2)

The Generator (simulated) removed the raw exception, but the replacement
code imports `app.modules.staff.repository` directly from inside
`activities` -- a real module-boundary violation, not a hypothetical one.

```
=== mypy . ===
Success: no issues found in 55 source files

=== ruff check . ===
All checks passed!

=== module boundary (AST) ===
src\app\modules\activities\_drill_scratch.py:18: from app.modules.staff.repository import ...

=== raw exception check ===
OK: none found
```

**Verdict: FAIL.** `scripts/check_module_boundaries.py` exited 1 and
printed the exact offending line -- this also independently confirms the
new AST-based checker (built to close a separate gap in this same
review -- see the note at the end of this file) correctly detects a real
cross-module repository import, not just correctly staying silent on
clean code.

## Iteration 3 -- unchanged, retry did not address the root cause

No code change from iteration 2 (representing a Generator retry that
misread the feedback and touched something else). Re-running the same
gate against the same code:

```
src\app\modules\activities\_drill_scratch.py:18: from app.modules.staff.repository import ...
```

**Verdict: FAIL.** Identical finding to iteration 2.

## Iteration 4 -- unchanged again

Same code, same gate, same result:

```
src\app\modules\activities\_drill_scratch.py:18: from app.modules.staff.repository import ...
```

**Verdict: FAIL.** Identical finding to iterations 2 and 3.

This byte-identical output across iterations 2-4 is itself the evidence
for the specific property `evaluator.md` and `how-to-review` claim:
"given the same check result, the verdict is always the same" -- not
asserted here, demonstrated with three independent runs producing the
same line.

## Escalation

Per `CLAUDE.md`'s state machine: `retry_count` reached 4 (initial attempt
+ 3 retries), which is `> 3`, so the orchestrator writes
`.harness/output/escalation.md` naming the sprint, the iteration count,
and the exact blocking issue copied from the last (iteration 4)
evaluator finding above, and stops -- no fourth retry. See
`.harness/output/escalation.md` for that artefact.

## Cleanup

`src/app/modules/activities/_drill_scratch.py` was deleted immediately
after iteration 4's output was captured. Re-running the full gate suite
afterward confirms the repository returned to a clean state (`mypy`: 54
source files, 0 issues; `ruff`: all checks passed; module-boundary
check: `OK: no cross-module repository imports`; raw-exception grep: no
match) -- identical to the state before this drill, confirming nothing
from the drill leaked into the real codebase.

## Why this file lives in `.harness/reviews/`, not `.harness/output/`

Everything else in `.harness/output/` is a working file for the *sprint
currently in flight* and is gitignored. This drill isn't a sprint and
produced no code -- but its evidence trail is exactly the kind of
governance artefact `.harness/reviews/` exists to hold permanently, so it
is committed here rather than discarded.
