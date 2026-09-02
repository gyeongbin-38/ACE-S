#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks" / "unseen-routing-v0.1.json"
EXPANSION = ROOT / "benchmarks" / "external-taxonomy-expansion-v0.2.json"


def pct(num: int, den: int) -> float:
    return round(100.0 * num / den, 1) if den else 0.0


def main() -> None:
    base = json.loads(BASE.read_text(encoding="utf-8"))
    expansion = json.loads(EXPANSION.read_text(encoding="utf-8"))

    cases = list(base["cases"]) + list(expansion["additional_cases"])
    active = [c for c in cases if c["expected_activation"] == "ACTIVE"]
    direct = [c for c in cases if c["expected_activation"] == "DIRECT"]
    covered = [c for c in active if not c.get("architecture_gap")]
    gaps = [c for c in active if c.get("architecture_gap")]

    result = {
        "experiment": "external-taxonomy-coverage-v0.2",
        "controller_commit": expansion["controller_commit"],
        "total_tasks": len(cases),
        "direct_tasks": len(direct),
        "active_tasks": len(active),
        "covered_active_tasks": len(covered),
        "gap_active_tasks": len(gaps),
        "taxonomy_coverage_rate_active": pct(len(covered), len(active)),
        "taxonomy_gap_rate_active": pct(len(gaps), len(active)),
        "gap_families": dict(Counter(c["architecture_gap"] for c in gaps)),
        "covered_primary_sets": dict(Counter("|".join(c["acceptable_primary"]) for c in covered)),
        "important_caveat": expansion["important_caveat"],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
