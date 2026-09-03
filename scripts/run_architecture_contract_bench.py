#!/usr/bin/env python3
"""Run authored architecture-contract fixtures against the deterministic validator."""
from __future__ import annotations

import json
from pathlib import Path

from validate_architecture_contract import validate

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmarks" / "architecture-contract-v0.2.json"


def main() -> None:
    obj = json.loads(SUITE.read_text(encoding="utf-8"))
    rows = []
    failed = []
    for case in obj["cases"]:
        result = validate(case["candidate"])
        errors = sorted({x["code"] for x in result["issues"] if x["severity"] == "error"})
        expected = sorted(set(case["expected_error_codes"]))
        ok = result["gate_passed"] == case["expected_gate_passed"] and errors == expected
        row = {
            "id": case["id"],
            "passed": ok,
            "gate_passed": result["gate_passed"],
            "error_codes": errors,
            "expected_gate_passed": case["expected_gate_passed"],
            "expected_error_codes": expected,
        }
        rows.append(row)
        if not ok:
            failed.append(row)

    report = {
        "suite_id": obj["suite_id"],
        "cases": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "rows": rows,
        "claim_boundary": obj["claim_boundary"],
    }
    print(json.dumps(report, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
