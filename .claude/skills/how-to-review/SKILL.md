---
name: how-to-review
description: The exact hard-gate commands and grep patterns the Evaluator runs, restated as a standalone checklist. Read this alongside architecture-principles before rendering any verdict.
---

# How to review a StoreOps sprint

Run every command below for real via Bash from the repository root (with
the project venv activated). Read the actual exit code / actual output --
never estimate.

## Dimension 1 checklist -- Architectural Compliance & Static Analysis (50%, hard gates)

1. **Types.** `mypy .` -- must print `Success: no issues found in N source
   files`. Any error is a FAIL.
2. **Lint.** `ruff check .` -- must print `All checks passed!`. Any error
   is a FAIL.
3. **Module boundary.** Zero cross-module repository imports:

   ```bash
   python3 - <<'EOF'
   import re, pathlib
   violations = []
   for path in pathlib.Path("src/app/modules").rglob("*.py"):
       module = path.parts[3]
       text = path.read_text()
       for m in re.finditer(r"from app\.modules\.(\w+)\.repository import", text):
           if m.group(1) != module:
               violations.append(f"{path}: imports {m.group(1)}.repository")
   print("\n".join(violations) or "OK: no cross-module repository imports")
   EOF
   ```

   Anything printed other than the `OK:` line is a FAIL -- quote the exact
   line in `evaluator-feedback.md`.

4. **Error contract.** Zero raw raises in services/routes:

   ```bash
   grep -rn "raise Exception\|raise HTTPException" src/app/modules/
   ```

   Any match is a FAIL. Quote the file and line.

5. **Event bus only.** For every diff that adds a cross-module write side
   effect, confirm it's an `event_bus.emit(...)` call in the emitting
   module's `service.py`, and that the receiving behaviour is a method in
   the *subscribing* module's `service.py` wired via
   `event_bus.subscribe(...)` in `app/main.py` -- not a direct import of
   the other module's service for the write. Grep to confirm:

   ```bash
   grep -rn "event_bus.emit\|event_bus.subscribe" src/app/
   ```

   If a sprint's contract implies a cross-module write and this grep
   shows no corresponding `emit`/`subscribe` pair, that's a FAIL: "missing
   event bus integration" (failure mode #4).

6. **Read-only reports.** If the sprint touched `reports/service.py`,
   confirm it only calls other modules' `*_service` read methods and only
   writes to `report_repository`. Any write call into another module's
   service/repository from `reports` is a FAIL.

**Any single FAIL above overrides Dimension 2 entirely -- render the
overall verdict as FAIL and skip straight to writing findings.**

## Dimension 2 checklist -- Functional Correctness & Verification (50%)

1. **Coverage.**

   ```bash
   pytest --cov=src/app --cov-report=json --cov-report=term-missing
   python scripts/check_coverage.py
   ```

   Read `check_coverage.py`'s exit code and printed per-layer breakdown
   directly -- do not recompute percentages by hand. Non-zero exit is a
   Dimension 2 FAIL naming which layer(s) missed threshold.

2. **AC-to-test traceability.** For each acceptance criterion in the
   sprint contract, open the test the Generator's self-check table points
   to and confirm it asserts a state change or a specific `AppError`
   subclass/code -- per `how-to-test`'s examples. A criterion backed only
   by a bare status-code assertion is a finding, worded exactly: "AC N
   satisfied by code but not verified by test," naming the test file and
   function.

## Rendering the verdict

- All of Dimension 1 passes + all of Dimension 2 passes -> **PASS**.
- All of Dimension 1 passes + exactly one small, documented Dimension 2
  gap -> **CONDITIONAL PASS** (log the gap, don't block).
- Anything else -> **FAIL**, with every finding as `file:line — rule
  violated`, specific enough that a Generator retry needs no
  clarification.

Given the same mypy/ruff/grep/pytest/check_coverage.py output, this
checklist always produces the same verdict -- that determinism is the
point; see `evaluator.md`'s verdict rules for the escalation fallback
when your own judgment on an AC is genuinely ambiguous.
