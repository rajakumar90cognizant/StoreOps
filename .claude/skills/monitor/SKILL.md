---
name: monitor
description: Runs the Monitor step of the StoreOps harness. Use when the developer types /monitor sprint-N after a verdict has been produced.
---

Delegate to the `monitor` subagent (`.claude/agents/monitor.md`). Pass it
the sprint number to archive. Do not write to `.harness/reviews/` here
yourself -- the subagent owns the audit trail.
