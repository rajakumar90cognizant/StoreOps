---
name: planner
description: Runs the Planner step of the StoreOps harness. Use when the developer types /planner <feature request> to start a new harness run.
---

Delegate to the `planner` subagent (`.claude/agents/planner.md`), passing
it the developer's feature request verbatim. Do not decompose the feature
or write any handoff files yourself -- that is the subagent's job, done in
its own fresh context. Once the subagent returns, tell the developer to
review `.harness/output/spec.md` and type `APPROVED` to proceed, or give
feedback if the decomposition needs changing before another `/planner`
pass.
