"""AST-based module-boundary hard gate.

Replaces the original single-pattern regex (`from app\\.modules\\.(\\w+)\\.
repository import`), which only caught one import form and would miss a
plain `import app.modules.X.repository`, an aliased
`import app.modules.X.repository as x`, or `from app.modules.X import
repository`. This walks the real AST of every file under
`src/app/modules/`, so it catches every syntactic way Python allows a
module to reach another module's repository layer, not just the one form
this codebase happens to use today.

A module importing its *own* repository (e.g. `activities/service.py`
importing `app.modules.activities.repository`) is allowed -- only a
*cross*-module repository import is a violation, per
`architecture-principles` rule 2.

Run from the repository root. Exit code 0 = no cross-module repository
imports. Exit code 1 = at least one violation, printed as
`<file>:<line>: <the import statement text>`. This is the exact script
`how-to-review/SKILL.md` and `evaluator.md`'s Dimension 1 hard gate #3
run -- see those files for how the Evaluator uses it.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

MODULES_ROOT = Path("src/app/modules")


def _owning_module(path: Path) -> str:
    """The module a file belongs to, e.g. `activities` for
    `src/app/modules/activities/service.py`."""
    return path.relative_to(MODULES_ROOT).parts[0]


def _repository_module_of(dotted: str) -> str | None:
    """If `dotted` is `app.modules.<module>.repository` (or a deeper
    attribute path into it), return `<module>`; else None."""
    prefix = "app.modules."
    if not dotted.startswith(prefix):
        return None
    segments = dotted[len(prefix) :].split(".")
    if len(segments) >= 2 and segments[1] == "repository":
        return segments[0]
    return None


def _violations_in_file(path: Path) -> list[str]:
    owning_module = _owning_module(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _repository_module_of(alias.name)
                if target is not None and target != owning_module:
                    violations.append(f"{path}:{node.lineno}: import {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            # from app.modules.<other>.repository import <names>
            target = _repository_module_of(module)
            if target is not None and target != owning_module:
                violations.append(f"{path}:{node.lineno}: from {module} import ...")
                continue

            # from app.modules.<other> import repository [as alias]
            if module.startswith("app.modules."):
                candidate_module = module[len("app.modules.") :]
                if "." not in candidate_module and candidate_module != owning_module:
                    for alias in node.names:
                        if alias.name == "repository":
                            violations.append(
                                f"{path}:{node.lineno}: from {module} import repository"
                            )

    return violations


def main() -> int:
    violations: list[str] = []
    for path in sorted(MODULES_ROOT.rglob("*.py")):
        violations.extend(_violations_in_file(path))

    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1

    print("OK: no cross-module repository imports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
