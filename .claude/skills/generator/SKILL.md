---
name: generator
description: Runs the Sprint N implementation step of the StoreOps harness. Use when the developer types /generator sprint-N after approving the spec.
---

Delegate to the `generator` subagent (`.claude/agents/generator.md`). Pass
it this sprint's approved `.harness/output/sprint-N-contract.md`, and on a
retry, the latest `.harness/output/evaluator-feedback.md` too. Do not
implement anything here yourself.
