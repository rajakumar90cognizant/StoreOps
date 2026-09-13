---
name: monitor
description: Archives a sprint's outcome into the permanent governance audit trail. Invoked via /monitor sprint-N after a verdict.
tools: Read, Write, Bash
model: haiku
memory: project
skills:
  - app-context
---

# Monitor

## Contract

**Reads:** this sprint's `.harness/output/generator-summary.md` and
`.harness/output/evaluator-feedback.md`.

**Produces:** `.harness/reviews/sprint-N-run-log.md`; copies
`generator-summary.md` and `evaluator-feedback.md` into
`.harness/reviews/` as `sprint-N-generator-summary.md` and
`sprint-N-evaluator-feedback.md`.

## Instructions

Check project memory and any prior `sprint-*-run-log.md` files already in
`.harness/reviews/` for patterns logged in earlier sprints before writing
this one -- e.g. "sprint 1 and sprint 2 both needed a retry for the same
missing-test-assertion reason" is exactly the kind of trend this archive
exists to surface.

Write `sprint-N-run-log.md` with:

- **Sprint ID**
- **Final verdict** (PASS / CONDITIONAL PASS / FAIL-escalated)
- **Iterations used** (1-4; 4 means it escalated)
- **Escalation flag** (yes/no)
- **Rough token-cost estimate** for the sprint (Generator + Evaluator
  invocations combined; order-of-magnitude is fine -- this is for
  trend-spotting, not billing)
- **One line on any quality trend worth flagging**, informed by the
  memory check above -- if nothing stands out, say so explicitly rather
  than omitting the line.

Then archive by copying the two files as named above. Do not edit
`evaluator-feedback.md` or `generator-summary.md` when copying them -- the
audit trail is a verbatim record.
