#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from architecture_pareto import frontier

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "benchmarks" / "architecture-frontier-v0.1.json"


def main() -> None:
    obj = json.loads(PATH.read_text(encoding="utf-8"))
    result = frontier(obj)
    expected = obj["expected"]
    hard = sorted(x["id"] for x in result["eliminated"] if x["reason"] == "hard_constraint")
    dominated = sorted(x["id"] for x in result["eliminated"] if x["reason"] == "dominated")
    unknown = sorted(result["unknown_material_dimensions"])
    checks = {
        "frontier": sorted(result["pareto_frontier"]) == sorted(expected["pareto_frontier"]),
        "hard_elimination": hard == sorted(expected["hard_eliminated"]),
        "dominance": dominated == sorted(expected["dominated"]),
        "unknown_blocking": unknown == sorted(expected["unknown_candidates"]),
        "no_fake_winner": result["winner"] is None,
    }
    report = {"suite_id": obj["suite_id"], "checks": checks, "result": result, "passed": all(checks.values()), "claim_boundary": obj["claim_boundary"]}
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
