# StoreOps

A retail **store operations management** REST API (FastAPI + Python),
built and governed end-to-end by a real Claude Code multi-agent harness --
the capstone project for Cognizant's AI-Native Tech Architect Programme
(Case Study 1, Build Track).

There are two things in this repository:

1. **StoreOps itself** -- a working API with five domain modules,
   in-memory storage, and an event-bus architecture (see below).
2. **The harness that builds it** -- `CLAUDE.md`, `.claude/agents/`,
   `.claude/skills/`, and `.harness/` are a governed Planner ->
   Generator -> Evaluator -> Monitor pipeline that adds new features to
   StoreOps autonomously, enforcing this project's architecture rules on
   every change.

If you just want to run the API and try the endpoints, skip to
[Quick start](#quick-start). If you want to understand or extend the
harness, skip to [The harness](#the-harness).

---

## What StoreOps does

Store teams use it to track day-to-day **activities** (restocking runs,
planogram resets, audits, compliance checks), organise **programmes**
(seasonal rollouts, compliance drives, store refits) and staff them,
receive **alerts** when something operationally relevant happens, and
look up **staff** (read-only). A fifth module, **reports**, aggregates
data across the others but isn't wired to an HTTP route yet in this
baseline.

Every module follows the same three layers -- **Routes -> Service ->
Repository** -- and the one architectural rule worth knowing up front:
**a write in one module never calls another module's code directly to
trigger a side effect.** It fires an event on an in-memory `EventBus`
instead, and the other module reacts to it. You'll see this in the API
itself: adding a staff member to a programme, or bulk-updating activity
statuses, both quietly create entries in `alerts` -- via the event bus,
never a direct import.

This isn't incidental -- it's the whole point of the project. See
[Why it's built this way](#why-its-built-this-way).

---

## Quick start

**Prerequisites:** Python 3.11+ on `PATH` (as `python` or `py`). Nothing
else -- the scripts below create their own virtual environment.

### Windows
```bat
start.bat
```

### macOS / Linux / Git Bash
```bash
./start.sh
```

Either script creates/reuses a `.venv`, installs/updates dependencies,
starts the API on `http://127.0.0.1:8010`, waits for it to report
healthy, and opens the Swagger UI in your browser automatically. Press
**Ctrl+C** to stop it, or run `stop.bat` / `./stop.sh` from another
window at any time to force-stop whatever's listening on the port. Both
start scripts also self-heal: if a previous run wasn't shut down cleanly
and left the port occupied, they detect and clear that before starting a
new one.

**Full endpoint reference, auth setup, and a worked walkthrough:**
see **[OPENAPI_TESTING.md](OPENAPI_TESTING.md)** -- read that next.

### Manual start (if you'd rather not use the scripts)
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### Docker
```bash
docker compose up --build
```
See [DEPLOYMENT.md](DEPLOYMENT.md) for what was actually verified for this
submission (this machine's environment didn't have Docker/WSL available,
so the demonstration run used the native path above -- the Dockerfile
runs the identical commands either way).

---

## Verifying the code

```bash
mypy .                                              # 0 errors, strict mode
ruff check .                                         # 0 lint errors
python scripts/check_module_boundaries.py            # AST-based module-boundary gate
pytest --cov=src/app --cov-report=term-missing       # tests + coverage
python scripts/check_coverage.py                     # per-layer coverage gate
```

`check_coverage.py` exists because this project's coverage thresholds are
per-architectural-layer (service ≥80%, routes ≥70%, shared utilities
≥60%, overall ≥70%) -- `coverage.py` alone only supports one global
threshold, not enough to catch a well-tested route layer masking a
thin service layer.

---

## Project structure

```
src/app/
  main.py                 -- FastAPI app, router wiring, the one AppError -> JSON handler
  core/                   -- shared infrastructure (errors, event bus, in-memory repo base, auth)
  modules/
    activities/           -- Routes -> Service -> Repository, one per module
    programmes/
    staff/                -- read-only from every other module
    alerts/
    reports/               -- read-only aggregator, no HTTP routes yet
tests/                     -- mirrors src/app/ module-for-module

CLAUDE.md                  -- harness orchestrator: commands, state machine, escalation rules
.claude/agents/             -- planner, generator, evaluator, monitor (real Claude Code subagents)
.claude/skills/              -- knowledge skills (architecture rules, conventions, review checklist)
                               + command skills (thin routers to each agent)
.harness/reviews/           -- permanent audit trail: one generator-summary + evaluator-feedback
                               + run-log per sprint, committed forever
.harness/output/             -- working files for the run in progress (gitignored)

start.bat / start.sh        -- one-command local startup (venv, deps, server, health check, browser)
stop.bat / stop.sh          -- explicit force-stop for whatever's on the port
scripts/check_coverage.py    -- per-layer coverage gate used by the Evaluator's hard gates

PROMPT.md                   -- the feature prompt used for this repo's demonstration run
DESIGN_BRIEF.md              -- the architectural reasoning behind the harness (start here for "why")
DEPLOYMENT.md                -- how the demonstration feature was deployed and verified
REFLECTION.md                 -- what the harness did well/fell short on, on its actual run
OPENAPI_TESTING.md            -- full endpoint reference, auth guide, worked walkthrough
```

---

## Why it's built this way

A prior AI-assisted coding experiment on this kind of codebase produced
four recurring failure modes: modules reaching directly into each
other's storage, raw exceptions instead of a typed error contract, tests
that check an HTTP status but never the actual business rule, and state
changes that skip the event bus entirely. Every rule in
`architecture-principles` and every hard gate in `how-to-review` maps
directly to preventing one of those four things -- not as a style
preference, but because each one is a specific, previously-observed way
this exact kind of system breaks. `DESIGN_BRIEF.md` Section B spells out
which skill file governs which rule and why; `REFLECTION.md` records what
actually happened -- including a real limitation -- when the harness was
run for real.

---

## The harness

Four real Claude Code subagents, each with its own scoped context and
skill files, drive a development loop:

```
/planner "<feature request>"
    -> spec.md (STATUS: AWAITING APPROVAL) + sprint-N-contract.md
    -> developer reviews, types APPROVED

/generator sprint-N
    -> implements exactly that sprint's scope, writes generator-summary.md

/evaluator sprint-N
    -> runs the real hard gates (mypy, ruff, coverage, module-boundary /
       raw-exception / event-bus greps) and produces a PASS / CONDITIONAL
       PASS / FAIL verdict in evaluator-feedback.md, with file+line detail
       on any failure

/monitor sprint-N
    -> archives the sprint to .harness/reviews/ as a permanent audit
       record, and checks project memory for cross-sprint quality trends
```

PASS advances to the next sprint. FAIL sends feedback back to the
Generator (up to 3 retries) before writing `.harness/output/escalation.md`
and stopping for a human. Full detail -- routing logic, context-reset
strategy, and how this relates to CI -- is in `CLAUDE.md`.

This repository's own demonstration run (`PROMPT.md`) added the "shift
handover bulk status update" feature across two sprints, both of which
passed on the first attempt -- the full evidence chain (contract ->
generated code -> evaluator verdict -> run log) is committed under
`.harness/reviews/`.

**One thing worth knowing if you re-run the harness in a sandboxed
environment:** the Generator and Evaluator subagents need real shell
execution to run their own hard gates. If that's blocked (as it was for
part of this project's own demonstration run -- see `REFLECTION.md`),
the Evaluator will correctly refuse to fabricate a verdict rather than
guess; you run the four commands from [Verifying the code](#verifying-the-code)
yourself and hand it the output.

---

## Further reading

| Document | What's in it |
|---|---|
| [OPENAPI_TESTING.md](OPENAPI_TESTING.md) | Every endpoint, auth setup, sample requests/responses, an 8-step walkthrough |
| [DESIGN_BRIEF.md](DESIGN_BRIEF.md) | Intent decomposition, governance framework, non-determinism strategy, key architectural decisions |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Deployment target, steps taken, live verification for the demonstration feature |
| [REFLECTION.md](REFLECTION.md) | What the harness did well, where it fell short, one concrete improvement |
| [CLAUDE.md](CLAUDE.md) | The orchestrator: commands, state machine, escalation, CI relationship |
| [PROMPT.md](PROMPT.md) | The exact feature prompt used to drive the demonstration run |
