"""Per-layer coverage threshold check.

`coverage.py` only supports a single global `fail_under`. StoreOps' rules
(Section 3.6 of the capstone spec) set different thresholds per
architectural layer:

    service layer   >= 80%
    route layer      >= 70%
    shared utilities >= 60%
    overall project  >= 70%

Run `pytest --cov=src/app --cov-report=json` first (writes coverage.json
to the repo root), then run this script. It is the exact command the
Evaluator subagent runs as one of its Dimension 2 hard gates -- see
.claude/agents/evaluator.md and .claude/skills/how-to-review/SKILL.md.

Exit code 0 = every threshold met. Exit code 1 = at least one violated
(the offending layer(s) are printed).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

THRESHOLDS = {
    "service": 80.0,
    "route": 70.0,
    "shared": 60.0,
    "overall": 70.0,
}


def _layer_for(path: str) -> str | None:
    normalized = path.replace("\\", "/")
    if "/core/" in normalized:
        return "shared"
    if normalized.endswith("service.py"):
        return "service"
    if normalized.endswith("routes.py"):
        return "route"
    return None


def main() -> int:
    coverage_path = Path("coverage.json")
    if not coverage_path.exists():
        print(
            "coverage.json not found. Run:\n"
            "  pytest --cov=src/app --cov-report=json --cov-report=term-missing\n"
            "before this script.",
            file=sys.stderr,
        )
        return 1

    data = json.loads(coverage_path.read_text(encoding="utf-8"))
    totals_by_layer: dict[str, list[float]] = {"service": [], "route": [], "shared": []}

    for file_path, file_data in data["files"].items():
        layer = _layer_for(file_path)
        if layer is None:
            continue
        percent = file_data["summary"]["percent_covered"]
        totals_by_layer[layer].append(percent)

    overall_percent = data["totals"]["percent_covered"]

    failures: list[str] = []
    results: list[str] = []

    for layer in ("service", "route", "shared"):
        values = totals_by_layer[layer]
        layer_avg = sum(values) / len(values) if values else 100.0
        threshold = THRESHOLDS[layer]
        status = "PASS" if layer_avg >= threshold else "FAIL"
        results.append(
            f"{layer:8s} layer: {layer_avg:6.2f}% (threshold {threshold:.0f}%) [{status}]"
        )
        if layer_avg < threshold:
            failures.append(layer)

    overall_status = "PASS" if overall_percent >= THRESHOLDS["overall"] else "FAIL"
    results.append(
        f"{'overall':8s}      : {overall_percent:6.2f}% "
        f"(threshold {THRESHOLDS['overall']:.0f}%) [{overall_status}]"
    )
    if overall_percent < THRESHOLDS["overall"]:
        failures.append("overall")

    print("\n".join(results))

    if failures:
        print(f"\nCOVERAGE GATE: FAIL -- below threshold: {', '.join(failures)}", file=sys.stderr)
        return 1

    print("\nCOVERAGE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
