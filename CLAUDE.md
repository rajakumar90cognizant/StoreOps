# StoreOps Development Harness

This file is read automatically by Claude Code whenever a session starts
in this repository. It is the orchestration brain of the harness described
in the Cognizant AI-Native Tech Architect capstone (Case Study 1, Build
Track): a governed Planner -> Generator -> Evaluator -> Monitor loop that
adds features to the StoreOps API without reintroducing the four failure
modes the programme's standards team flagged in a prior AI-coding
experiment (cross-module repository imports, raw exception throws,
status-code-only tests, missing event-bus integration).

## Commands

| Command | Subagent | Produces |
|---|---|---|
| `/planner <feature request>` | `.claude/agents/planner.md` | `.harness/output/spec.md` (ends with the literal line `STATUS: AWAITING APPROVAL`), one `.harness/output/sprint-N-contract.md` per sprint |
| `/generator sprint-N` | `.claude/agents/generator.md` | Code under `src/app/`, tests under `tests/`, `.harness/output/generator-summary.md` |
| `/evaluator sprint-N` | `.claude/agents/evaluator.md` | `.harness/output/evaluator-feedback.md` with a PASS / CONDITIONAL PASS / FAIL verdict |
| `/monitor sprint-N` | `.claude/agents/monitor.md` | `.harness/reviews/sprint-N-run-log.md`, and copies that sprint's `generator-summary.md` + `evaluator-feedback.md` into `.harness/reviews/` |

Each command is a thin routing Skill under `.claude/skills/<command>/SKILL.md`
that does nothing itself except hand the work to the matching subagent.
See "Why each step is a real subagent" below for why the work happens
there and not inline in this conversation.

## State machine

```
developer: /planner <feature request>
   -> planner writes spec.md + sprint-N-contract.md(s), ends spec.md with
      "STATUS: AWAITING APPROVAL", and stops.

developer reviews spec.md, types: APPROVED
   -> loop begins at sprint 1:

        generator implements sprint-N-contract.md
            -> writes code + tests + generator-summary.md

        evaluator reviews the sprint
            -> writes evaluator-feedback.md with verdict
               PASS | CONDITIONAL PASS | FAIL

        PASS or CONDITIONAL PASS:
            monitor archives the sprint -> sprint-N-run-log.md in
            .harness/reviews/, then advance to the next sprint
            (or stop if this was the last sprint contract)

        FAIL:
            retry_count += 1
            if retry_count <= 3:
                generator re-runs sprint N, reading the just-written
                evaluator-feedback.md this time
            else:
                write .harness/output/escalation.md naming the sprint,
                the iteration count (4), and the exact blocking issue(s)
                copied from the last evaluator-feedback.md, and STOP.
                A human resolves it from here -- the loop does not
                retry a fourth time.
```

The orchestrating Claude Code session (the one reading this file) is what
reads `evaluator-feedback.md`'s verdict line and decides which of the
three branches above to take -- that routing logic lives here, not inside
any one subagent, because no single subagent needs to know about the
other three's outputs beyond the one handoff file it was handed.

## Why each step is a real subagent, not one long conversation

Every one of planner/generator/evaluator/monitor is invoked as its own
Claude Code subagent (a real Task-tool invocation against
`.claude/agents/*.md`), never a persona switch inside a single,
ever-growing conversation. Two concrete reasons:

1. **Fresh context per step.** A multi-sprint run can touch a dozen files
   across code, tests, and three separate markdown handoff documents. If
   Planner, Generator, and Evaluator all shared one context window,
   sprint 3's Evaluator would be reasoning with the accumulated noise of
   sprints 1 and 2's back-and-forth still sitting in context -- degrading
   exactly the kind of judgment call ("is this AC really satisfied?") this
   harness depends on. A fresh subagent invocation means the Evaluator for
   sprint 3 sees only: the `architecture-principles` and `how-to-review`
   skills, this sprint's contract, and this sprint's
   `generator-summary.md`. Nothing else.
2. **Narrow, auditable inputs.** Because each subagent only reads what its
   `.claude/agents/*.md` file says it reads, the handoff files
   (`spec.md`, `sprint-N-contract.md`, `generator-summary.md`,
   `evaluator-feedback.md`) are the *entire* interface between steps. If a
   verdict looks wrong, you can point at exactly what the Evaluator saw
   and reproduce its reasoning from those files alone -- no need to
   reconstruct it from a sprawling transcript.

## Context scoping strategy

- **Planner** reads: `app-context`, `architecture-principles`,
  `sprint-decomposition` skills, and the developer's raw feature prompt.
  Nothing from `src/` unless it greps for an existing pattern to confirm
  scope.
- **Generator** reads: `app-context`, `architecture-principles`,
  `coding-conventions`, `component-patterns`, `how-to-test` skills, plus
  the one sprint contract for this invocation (and, on retry, the one
  prior `evaluator-feedback.md` -- never earlier sprints' feedback).
- **Evaluator** reads: `architecture-principles`, `how-to-review` skills,
  plus `spec.md`, this sprint's `generator-summary.md`, and whichever
  changed files it names from that summary.
- **Monitor** reads: `app-context` skill, plus this sprint's
  `generator-summary.md` and `evaluator-feedback.md`, and (via project
  memory / prior `run-log.md` files already in `.harness/reviews/`) past
  sprints' outcomes to spot trends.

No subagent reads another sprint's handoff files unless it is the current
sprint. That is what "context reset between agent invocations" means in
practice here: every invocation starts cold, bounded to one sprint's worth
of material, which keeps token cost roughly constant per sprint regardless
of how many sprints a feature ends up needing -- and is the "cost-aware
skill file design" trade-off this capstone asks for: the knowledge skills
are detailed enough to be StoreOps-specific, but no agent ever loads more
than the ~4-5 skills its own row in the table above lists.

## Relationship to CI/CD

The Evaluator's hard gates are exactly the same commands, run the same
way, natively and inside Docker:

```
mypy . && ruff check . \
  && pytest --cov=src/app --cov-report=json --cov-report=term-missing \
  && python scripts/check_coverage.py
```

This harness **precedes** CI -- it does not replace it. The harness runs
these checks locally, inside the Generator/Evaluator loop, before a human
ever opens a pull request. Whatever CI pipeline this repository is
eventually wired to (not part of this capstone) would run the identical
commands again on the PR -- a PASS verdict from the Evaluator should mean
CI passes too, with no surprises at the pipeline stage. This is also why
harness files live under `.harness/` and not `.github/`: this project's
governance artefacts are deliberately kept separate from whatever CI/CD
configuration a real client's pipeline would add on top of this repo.
