# Harness Design Brief

**Project:** StoreOps development harness (Cognizant AI-Native Tech
Architect Programme, Capstone Case Study 1, Build Track)
**Demonstration feature:** Shift handover bulk status update
(`PATCH /api/activities/bulk-status`)

---

## Section A -- Intent Decomposition

### How the feature was broken into sprint contracts

The Planner subagent (`.claude/agents/planner.md`) received one prompt --
the exact text in `PROMPT.md` -- and produced `spec.md` plus two sprint
contracts, without being told in advance how many sprints to use. It drew
the boundary at the one place `architecture-principles` rule 3 (event bus
only for cross-module writes) forces a seam: "an audit entry per updated
task" means an `activities` write has to cause a record to appear in
`alerts`, and that can only happen through `event_bus.emit`/`subscribe`,
never a direct import. So:

- **Sprint 1** owns the entire mutation inside `activities`: the new
  endpoint, the service method, partial-failure handling, and the
  `event_bus.emit("activity.bulk_status_updated", payload)` call --
  deliberately **without** a subscriber yet.
- **Sprint 2** owns only the subscriber side inside `alerts`: one new
  handler method plus the one-line `event_bus.subscribe(...)` addition to
  `app/main.py`.

This wasn't an arbitrary split for parallelism -- it's the same seam
`sprint-decomposition` documents ("a sprint that touches more than one
module's `service.py` for a write is almost always a sign the feature
needs an event-bus wiring sprint of its own"), and it meant each half was
independently testable: sprint 1's tests only need `activities` and a
test-subscribed handler (mirroring `tests/core/test_event_bus.py`'s
pattern) to prove the emit fires with the right payload; sprint 2's tests
only need `alerts` plus one end-to-end test that imports `app.main` to
prove the wiring is real, not asserted in isolation.

### Acceptance criteria structure

Every AC in both contracts is GIVEN/WHEN/THEN, and every one names a
concrete state check or a concrete typed error rather than a behavioural
generality -- per `sprint-decomposition`'s rule that an AC must be
answerable by (1) a specific state change readable back through an
existing method/endpoint, (2) a specific `AppError` subclass, or (3) a
specific `event_bus.emit` payload contract. That constraint is what made
the Evaluator's job mechanical rather than judgment-heavy: for each AC,
"is there a test that satisfies this" is a traceability check, not a
debate.

### One sprint contract entry, in full

From `sprint-1-contract.md`, AC 3:

> GIVEN an empty `updates` list, WHEN
> `activity_service.bulk_update_status` is called, THEN a
> `ValidationError` (from `app.core.errors`) is raised, and no
> `"activity.bulk_status_updated"` event is captured by a test-subscribed
> handler (i.e. zero side effects occurred).

This is testable in one assertion block (and was --
`test_bulk_update_status_rejects_empty_updates_with_no_side_effects` in
`tests/modules/activities/test_service.py`), names the exact exception
type, and closes the loop on the *negative* case: not just "it rejects
empty input" but "it rejects it with zero side effects," which is what
made this AC catch a real design question (should an empty batch still
attempt to emit anything?) before the Generator wrote a line of code.

---

## Section B -- Governance Framework

### Skill file strategy

| Skill | Governs | Shared across |
|---|---|---|
| `app-context` | The 5-module glossary: entities, enums, seeded demo users/tokens | All four agents |
| `architecture-principles` | The 5 non-negotiable rules (layering, module boundary, event-bus-only, AppError contract, read-only reports) | All four agents |
| `sprint-decomposition` | How to draw sprint boundaries and write testable ACs | Planner only |
| `coding-conventions` | Real idioms from the baseline: `StrEnum`, `model_copy(update=...)`, module-level singletons, `datetime.now(UTC)` | Generator only |
| `component-patterns` | The exact `EventBus.emit`/`AppError`/`InMemoryRepository` call shapes, copied verbatim from the baseline | Generator only |
| `how-to-test` | Fixtures, coverage thresholds, worked examples of state-assertion vs. status-code-only tests | Generator only |
| `how-to-review` | The exact hard-gate commands and grep patterns, restated as a standalone checklist | Evaluator only |

`app-context` and `architecture-principles` are shared everywhere because
they're the two things every agent needs regardless of role: what exists,
and what's forbidden. Everything else is scoped to exactly one agent
because loading `coding-conventions` into the Evaluator (say) would mean
it's reasoning about style it has no mandate to enforce, and loading
`how-to-review`'s grep commands into the Generator would let it "check
its own homework" against the literal Evaluator checklist instead of just
building it right the first time.

### The audit trail

`.harness/reviews/` captured, for real, in this run:
`sprint-1-{generator-summary,evaluator-feedback,run-log}.md` and the same
for sprint 2 -- six files, all committed, none edited after being
written. `sprint-N-run-log.md` records verdict, iterations used (both
sprints: 1, no retries), escalation flag (both: no), a token-cost
estimate, and a quality-trend note. Anyone with repo access can read
these without re-running anything. The Monitor also writes to Claude
Code's own project memory (`.claude/agent-memory/monitor/`) -- after
sprint 1 it recorded "both sprints passed first-try with strong
architecture discipline," and that observation was available to sprint
2's Monitor invocation as prior context. If a *third* sprint had failed
after two clean passes, that memory file plus the run-logs are exactly
what would let a reviewer (or the next Monitor invocation) say "this
broke a two-sprint streak" instead of treating it as an isolated event --
that's how this archive would surface a recurring quality issue: not by
alerting on a single FAIL, but by making the *sequence* of verdicts
visible in one place.

### One skill file rule, and what breaks without it

From `architecture-principles`, rule 3: *"A write in one module that
needs to cause a side effect in another module must go through
`event_bus.emit(event_name, payload)` ... never a direct import of the
other module's service to perform that write."* Without it, the
Generator's most natural first draft of "audit entry per updated task"
would have been `activities/service.py` importing `alert_service` and
calling `create_notification` directly inline in `bulk_update_status` --
fewer files, one sprint instead of two, no event payload contract to get
right. It would also have been exactly failure mode #4 from the
capstone's client context ("missing event bus integration -- state
changes written directly to sibling module repositories"), and it would
have made `activities` untestable without also loading `alerts`, and
un-deployable independently of it. The rule is what forced the two-sprint
split in Section A, and the Evaluator's Dimension 1 hard gate 5 (grep for
`event_bus.emit`/`subscribe` pairing) is what would have caught it if the
Generator had ignored the constraint anyway.

---

## Section C -- Non-Determinism Strategy

### Dimensions and weights

- **Dimension 1 -- Architectural Compliance & Static Analysis (50%).**
  mypy, ruff, the module-boundary grep script, the raw-exception grep,
  and the event-bus-pairing grep. All five are automated and binary.
- **Dimension 2 -- Functional Correctness & Verification (50%).**
  `pytest --cov` + `scripts/check_coverage.py`'s per-layer thresholds,
  plus AC-to-test traceability (does every acceptance criterion have a
  state-asserting test, not a status-code-only one).

50/50 because this capstone's four named failure modes split evenly
across the two: cross-module imports and raw exceptions are static
*compliance* problems (Dimension 1); status-code-only tests and missing
event-bus integration are *verification* problems you can only catch by
looking at what the tests actually assert and what actually fires at
runtime (Dimension 2). Weighting either one higher would mean tolerating
more of the failure modes that dimension exists to catch.

### Hard gates, and why they can't be soft

Every Dimension 1 check is a hard gate -- a single FAIL there overrides
Dimension 2 entirely -- because each one is the literal, direct
encoding of one of the four named failure modes, and "mostly compliant"
isn't a real state for any of them: code either has a raw
`raise Exception(...)` in it or it doesn't; a module either imports
another module's repository or it doesn't. A soft/scored version of
"zero cross-module repository imports" would mean the Evaluator could
average a violation away against otherwise-good code, which is precisely
what let the four failure modes reach `main` in the client's original
experiment. A soft check makes sense for style opinions where reasonable
disagreement exists; it does not make sense for "did this bypass the
governed service boundary."

### Verdict determinism, walked through

This run's actual sprint 1: mypy returned "no issues found in 53 source
files," ruff returned "All checks passed!," the module-boundary script
returned "OK: no cross-module repository imports," the raw-exception grep
returned nothing, and the event-bus grep showed the new `emit` call with
no corresponding subscriber yet (correct -- sprint 1 is emit-only by
contract). All five Dimension 1 gates pass -> Dimension 2 runs:
`check_coverage.py` printed `service 97.38%`, `route 100%`, `shared
100%`, `overall 98.78%`, all above threshold, exit 0; all 5 ACs traced to
state-asserting tests (verified by reading the actual test bodies, not
the Generator's self-report). Every input to that decision was a
literal exit code or grep line -- given the identical five outputs, the
verdict is PASS every time, by construction, because the verdict rule
*is* "all Dimension 1 gates pass AND all Dimension 2 thresholds met AND
every AC traced," not a holistic judgment call layered on top of them.

**One real deviation worth recording honestly:** in this run's actual
execution environment, neither the Generator nor the Evaluator subagent
could execute the gate commands themselves (their sandbox blocked
interpreter execution non-interactively even with `Bash` granted) -- so
the developer ran the four commands from a working shell and pasted the
literal output back in. The verdict logic above is unchanged by that; the
inputs to it are real command output either way. See `REFLECTION.md` for
what that implies about full autonomy in this environment.

### Escalation path

If a sprint FAILs three consecutive Generator retries, the orchestrator
(per `CLAUDE.md`'s state machine) writes `.harness/output/escalation.md`
naming the sprint, the iteration count, and the exact blocking issue
copied from the last `evaluator-feedback.md`, and stops -- no fourth
retry. Neither sprint in this run reached that path (both PASSed on
iteration 1). The Evaluator did, however, demonstrate the *other* stop
condition this design relies on: when it couldn't execute its own hard
gates, it did not guess a verdict and did not retry blindly against an
un-retriable problem -- it wrote an honest FAIL naming the real blocker
and asked the developer directly, which is the correct fallback for
"the Evaluator's own output is ambiguous" (here, ambiguous because it had
no real check results yet, not because the code was in doubt).

---

## Section D -- Architectural Decisions

### Decision 1: Real Claude Code subagents via the Task-tool mechanism, driven by a nested `claude` CLI process, not simulated in one conversation

**Alternatives considered:** (a) simulate all four roles inside one
long-running conversation by switching persona per step; (b) build the
four roles as real `.claude/agents/*.md` subagents but only ever invoke
them from within the same orchestrating Claude Code session that
authored them (no separate process).

**Rationale:** (a) was explicitly ruled out by this capstone's own brief
-- a simulated harness can't demonstrate context-reset-between-agents or
prove the handoff files are the *actual* interface rather than something
the same context window could paper over from memory. (b) is closer, and
is in fact what happens naturally inside a single Claude Code session
(the Task tool does give each subagent invocation fresh context) -- but
this build went one step further and drove the whole Planner-approval-
Generator-Evaluator-Monitor sequence through a second, independent
`claude -p`/`-c` process against this repository, so that "real subagent"
also means "a genuinely separate Claude Code invocation reading
`CLAUDE.md` and `.claude/agents/*.md` off disk," not an assumption about
how the authoring session happens to behave.

**Assumption this depends on:** that the target environment allows
spawning a `claude` CLI process non-interactively with tool access. That
assumption held here only after the authoring session's own safety
classifier was satisfied that this was the user's explicit, informed
choice (see `REFLECTION.md`) -- it is not something a harness should
assume is available by default in every environment.

### Decision 2: `.harness/` instead of `.github/` for governance artefacts

**Alternatives considered:** (a) put skill files and agent definitions
under `.github/` alongside whatever CI workflow files a real client
pipeline would eventually add; (b) a separate top-level `.harness/`
namespace, as built.

**Rationale:** CI configuration and harness governance artefacts answer
different questions and have different audiences -- CI answers "does
this PR merge," the harness answers "should this AI-generated diff exist
at all, and why." Keeping them apart means a future CI pipeline can be
added to `.github/` without touching, reorganising, or being confused
with `.harness/reviews/`'s permanent audit trail.

**Assumption this depends on:** that this repository will eventually gain
a real CI pipeline distinct from this harness -- if it never does, the
separation still costs nothing, but the benefit (avoiding namespace
collision) goes unrealised.

### Decision 3: Coverage thresholds enforced by a custom script, not `coverage.py`'s single global `fail_under`

**Alternatives considered:** (a) accept one global coverage threshold
(simpler, native to `coverage.py`); (b) `scripts/check_coverage.py`,
parsing `coverage.json` and applying different thresholds per
architectural layer (service/route/shared/overall), as built.

**Rationale:** the capstone's own thresholds are explicitly per-layer
(80/70/60/70) because a service-layer bug is more consequential than an
undertested route handler that mostly just delegates -- a single global
number would let a well-tested route layer mask a genuinely undertested
service layer, which is exactly the layer `architecture-principles` rule
1 says holds all the business logic worth protecting.

**Assumption this depends on:** that file-path conventions
(`*/service.py`, `*/routes.py`, `app/core/*.py`) reliably identify a
file's layer -- true for every file in this baseline, but a future module
that breaks that naming convention would silently fall out of all three
per-layer buckets and only count toward "overall."
