# Architecture Journal

This is the informal record `DESIGN_BRIEF.md` deliberately isn't: not the
four rubric-shaped sections, just the decisions, trade-offs, and
surprises that came up while building this harness and running it for
real, in roughly the order they happened. Where `DESIGN_BRIEF.md` or
`REFLECTION.md` already cover something in full, this points at them
instead of repeating them.

## Starting from a stub, not a blank page

StoreOps' three-layer shape (Routes -> Service -> Repository), the
`AppError` hierarchy, and the `EventBus` all needed to exist *before* any
skill file could say anything StoreOps-specific -- a skill file that
says "use the typed error hierarchy" is empty if there's no hierarchy yet
to point at. That ordering (build the thing worth governing first, then
write the governance) turned out to matter more than expected: the
skill files that quote real code (`component-patterns` quoting the exact
`MEMBER_ADDED_EVENT` constant and handler shape from `programmes/service.py`)
are the ones that hold up; the temptation, if the harness had been
designed first, would have been to write "use an event bus for
cross-module writes" as a principle with no worked example to point at.

## Four agents, and what actually turned out to be the hard part

The hard part of splitting Planner/Generator/Evaluator/Monitor wasn't
inventing four roles -- the capstone brief hands you those. It was
deciding what each one is *not* allowed to read. `evaluator.md`
deliberately does not get `coding-conventions` or `component-patterns`;
`generator.md` deliberately does not get `how-to-review`'s grep
commands. The reasoning in `CLAUDE.md`'s "Context scoping strategy"
section states the conclusion; the actual back-and-forth was realizing
that giving the Generator the Evaluator's exact checklist would turn
"build it right" into "grep for the checklist and satisfy the letter of
it," which is a subtly worse failure mode than the one being guarded
against.

## Sprint decomposition caught a design question before code existed

Writing `sprint-1-contract.md`'s AC 3 -- the empty-`updates`-list case --
is the moment this harness earned its keep as something more than
ceremony. "An audit entry per updated task" doesn't obviously raise the
question "what happens with zero tasks?" until you're forced to write a
GIVEN/WHEN/THEN for it, and the honest answer (`ValidationError`, zero
events, per `architecture-principles` rule 4) was a real decision, not a
formality. `sprint-decomposition`'s rule that every AC must point at a
state change, a typed error, or an event payload -- not "the system
behaves correctly" -- is what forced that question to surface before the
Generator wrote a line of `bulk_update_status`.

## The Evaluator's 50/50 split was almost 70/30

Weighting Dimension 1 (static compliance) higher than Dimension 2
(functional correctness) was briefly tempting, on the logic that the
four named failure modes are architectural, so architecture should count
for more. The reason 50/50 won: two of the four failure modes
(status-code-only tests, missing event-bus integration) are only visible
by looking at what a test *asserts* and what actually *fires* at
runtime -- that's Dimension 2's job, not Dimension 1's. Weighting it
lower would have meant under-checking exactly half of what this harness
exists to prevent. `DESIGN_BRIEF.md` Section C states this decision;
this is the reasoning that almost went the other way.

## Running it for real surfaced a gap no design review would have caught

Both demonstration sprints (`sprint-1`, `sprint-2`) passed on the first
attempt -- which is good news about the harness's design, but it also
meant the retry path and the escalation path were, until an outside
architecture review flagged it, completely unexercised. The Evaluator's
"never guess PASS, fail honestly on ambiguity" rule did get tested for
real, though not the way it was meant to be: the sandbox blocked
`mypy`/`ruff`/`pytest` execution entirely for both sprints, and the
Evaluator correctly refused to fabricate a verdict rather than paper over
it -- see `REFLECTION.md` for the full account. That's the right
behaviour, but it's a workaround for an environment problem, not proof
the *retry-then-escalate* logic itself works.

## Post-review hardening (after initial submission)

An external architecture review of this repository -- checking every
claim against re-executed commands rather than the markdown's word for
it -- came back with the harness's evidence chain fully verified (every
coverage number, every grep result, every line reference it checked
matched real re-execution exactly), but surfaced three real gaps worth
recording honestly here rather than only in a review document that isn't
part of the harness itself:

1. **The module-boundary hard gate was a single regex**
   (`from app\.modules\.(\w+)\.repository import`), which only catches
   one of the several ways Python lets a module reach into another
   module's repository (a plain `import app.modules.X.repository`, or an
   aliased import, would have slipped past it undetected). Fixed by
   replacing it with `scripts/check_module_boundaries.py`, a real AST
   walk over every `Import`/`ImportFrom` node -- verified to still pass
   clean on the real codebase, and verified to actually catch every
   import form the old regex missed, via a throwaway test file that was
   then deleted.

2. **The escalation path had never fired.** Both sprints passed on the
   first try, which meant `CLAUDE.md`'s retry-then-escalate logic was
   fully specified but never proven against a real FAIL. Rather than
   leave that unverified, a deliberate drill (`.harness/reviews/
   escalation-drill-log.md`) ran four real iterations against a
   throwaway file -- a raw-exception violation, then a module-boundary
   violation that persisted unfixed across three more attempts -- with
   genuine `mypy`/`ruff`/`check_module_boundaries.py` output each time,
   and let the real escalation fire, producing a real
   `escalation.md`. The interesting part: iterations 2 through 4
   produced byte-identical command output, which is itself the concrete
   proof of the determinism property `evaluator.md` claims ("given the
   same check result, the verdict is always the same") -- not asserted,
   demonstrated.

3. **Running the drill exposed a second, unrelated bug it wasn't looking
   for.** `.gitignore` excludes the whole `.harness/output/` directory,
   and git will not apply a negation rule to a file inside a directory
   that's excluded at the directory level -- so the original
   `!.harness/output/escalation.md` fix silently did nothing, confirmed
   by `git check-ignore` still reporting it ignored. The actual fix
   (`.harness/output/*` instead of `.harness/output/`, so the exclusion
   is per-file rather than per-directory) only surfaced because the
   drill produced a real `escalation.md` and then checked whether `git
   add` would actually pick it up -- a design review reading the
   `.gitignore` file in isolation would very plausibly have missed this,
   since the negation rule *looks* correct on paper.

**The pattern across all three:** none of them were found by reasoning
about the design in the abstract. All three were found by actually
running the thing and checking the real output against what was
claimed -- which is, not coincidentally, the exact discipline this
harness asks of its own Evaluator.
