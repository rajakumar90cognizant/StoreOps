---
name: evaluator
description: Runs the Evaluator step of the StoreOps harness. Use when the developer types /evaluator sprint-N after the generator finishes a sprint.
---

Delegate to the `evaluator` subagent (`.claude/agents/evaluator.md`). Pass
it the sprint number to review. Do not run the hard-gate checks or render
a verdict here yourself -- that judgment belongs entirely to the
subagent, working from a fresh context bounded to this one sprint's
files.
