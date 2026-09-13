# .harness/reviews/ -- permanent governance audit trail

Every file in this directory (other than this README) is committed, never
gitignored, and never edited after the fact. Per sprint N, `monitor.md`
writes:

- `sprint-N-run-log.md` -- verdict, iterations used, escalation flag,
  token-cost estimate, quality-trend note.
- `sprint-N-generator-summary.md` -- verbatim copy of that sprint's
  `generator-summary.md`.
- `sprint-N-evaluator-feedback.md` -- verbatim copy of that sprint's
  `evaluator-feedback.md`.

This is the record a reviewer (or a future Evaluator, via project memory)
uses to answer "did this kind of failure happen before, and how often?"
without re-running anything. Compare against `.harness/output/`, which
holds the same-named *working* files for the sprint currently in flight --
those are gitignored and overwritten on every retry; only what lands here
survives.
