# Reflection

## What the harness did well

The Planner caught the one architecturally significant thing in the
feature request without being told to look for it: "an audit entry per
updated task" is a cross-module write (`activities` -> `alerts`), so it
split the feature into two sprints along exactly the seam
`sprint-decomposition` describes -- emit in sprint 1, subscribe in sprint
2 -- and wrote a `spec.md` constraint explicitly forbidding
`activities/service.py` from importing `alerts.service`. Both sprints
then passed on the **first** Generator/Evaluator iteration, with zero
retries: `mypy`, `ruff`, and the module-boundary/raw-exception/event-bus
greps came back clean both times, coverage stayed at 97-100% across every
layer, and every acceptance criterion traced to a state-asserting test
(re-fetch-and-check, not a bare status code) -- including a genuine
end-to-end test that imports `app.main` to exercise the real
`activities -> event_bus -> alerts` wiring rather than mocking it. The
Monitor's project memory worked as designed: after sprint 1 it recorded
"both sprints passed first-try with strong architecture discipline" and
carried that observation into sprint 2's run-log, which is the exact
trend-spotting behaviour `.harness/reviews/` is meant to enable.

## Where it fell short

The loop was not, in the end, fully autonomous in this execution
environment. Both the Generator and Evaluator subagents were granted
`Bash` in their frontmatter, and the orchestrating session was launched
with `--allowedTools "Bash"` -- but this sandbox's non-interactive
classifier still blocked every attempt to execute an actual interpreter
(`mypy`, `ruff`, bare `python`) from inside that session, for the
subagents and for the orchestrator's own fallback attempt alike. The
Evaluator did the right thing when it hit this: it refused to fabricate a
PASS, wrote a FAIL naming the real blocker (tooling execution, not a code
defect), and asked for help instead of burning its three retries against
a problem retrying can't fix. But that's a workaround, not the design --
the developer ended up running `mypy && ruff check && pytest --cov &&
check_coverage.py` by hand for both sprints and pasting the output back
in, which is exactly the manual step this harness exists to remove.

## One concrete improvement

Pre-approve the four hard-gate commands (`mypy .`, `ruff check .`,
`pytest --cov=src/app ...`, `python scripts/check_coverage.py`) as an
explicit allowlisted Bash rule in this project's Claude Code settings,
scoped narrowly enough that it doesn't weaken the sandbox generally.
That turns "the Evaluator can't run its own gates" from a structural gap
into a one-time configuration step, and would let a re-run of this exact
sprint sequence complete without a human relaying command output by hand
-- restoring the autonomy the state machine in `CLAUDE.md` describes.
