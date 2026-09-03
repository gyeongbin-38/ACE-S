#!/usr/bin/env python3
"""Calibrate incremental Architecture State Graph recomputation semantics."""
from __future__ import annotations

import json
from pathlib import Path

from architecture_impact import impact

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "architecture-state-graph-valid-v0.1.json"

CASES = [
    {
        "id": "asr-change",
        "changed": ["asr-tenant-isolation"],
        "expected_decisions": ["dec-store"],
        "expected_architecture": ["checkout-flow", "orders"],
        "expected_fitness": ["fit-tenant"],
        "expected_scenarios": ["scenario-cross-tenant"],
        "expected_proofs": [],
        "max_reopen_fraction": 0.40,
    },
    {
        "id": "state-change",
        "changed": ["orders"],
        "expected_decisions": ["dec-store"],
        "expected_architecture": ["orders"],
        "expected_fitness": [],
        "expected_scenarios": [],
        "expected_proofs": [],
        "max_reopen_fraction": 0.20,
    },
    {
        "id": "trust-boundary-change",
        "changed": ["tenant-boundary"],
        "expected_decisions": [],
        "expected_architecture": ["tenant-boundary"],
        "expected_fitness": ["fit-tenant"],
        "expected_scenarios": ["scenario-cross-tenant"],
        "expected_proofs": ["proof-tenant"],
        "max_reopen_fraction": 0.10,
    },
    {
        "id": "selected-option-change",
        "changed": ["opt-single-store"],
        "expected_decisions": ["dec-store"],
        "expected_architecture": ["orders"],
        "expected_fitness": [],
        "expected_scenarios": [],
        "expected_proofs": [],
        "max_reopen_fraction": 0.25,
    },
    {
        "id": "evidence-change",
        "changed": ["ev-auth-test"],
        "expected_decisions": [],
        "expected_architecture": [],
        "expected_fitness": ["fit-tenant"],
        "expected_scenarios": [],
        "expected_proofs": [],
        "max_reopen_fraction": 0.20,
    },
    {
        "id": "unlinked-requirement-change",
        "changed": ["req-checkout"],
        "expected_decisions": [],
        "expected_architecture": [],
        "expected_fitness": [],
        "expected_scenarios": [],
        "expected_proofs": [],
        "max_reopen_fraction": 0.10,
    },
]


def main():
    graph = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = []
    failed = []
    for case in CASES:
        result = impact(graph, case["changed"])
        checks = {
            "status": result.get("status") == "ok",
            "decisions": result.get("reopened_decisions") == case["expected_decisions"],
            "architecture": result.get("impacted_architecture") == case["expected_architecture"],
            "fitness": result.get("rerun_fitness_checks") == case["expected_fitness"],
            "scenarios": result.get("rerun_scenarios") == case["expected_scenarios"],
            "proofs": result.get("reprove_obligations") == case["expected_proofs"],
            "bounded_reopen": result.get("reopen_fraction", 1.0) <= case["max_reopen_fraction"] + 1e-12,
        }
        row = {
            "id": case["id"],
            "passed": all(checks.values()),
            "checks": checks,
            "reopen_fraction": result.get("reopen_fraction"),
            "impacted_node_ids": result.get("impacted_node_ids"),
        }
        rows.append(row)
        if not row["passed"]:
            failed.append({"case": case, "result": result, "checks": checks})

    negative = impact(graph, ["does-not-exist"])
    negative_ok = negative.get("status") == "unknown_changed_node"
    if not negative_ok:
        failed.append({"id": "unknown-node-negative", "result": negative})

    report = {
        "suite_id": "architecture-incremental-impact-v0.1",
        "cases": len(rows),
        "passed": sum(1 for r in rows if r["passed"]),
        "unknown_node_fail_closed": negative_ok,
        "rows": rows,
        "claim_boundary": "Authored graph-neighborhood calibration only. Bounded reopen fractions are not evidence of real-project architecture maintenance savings until measured on external graphs.",
    }
    print(json.dumps(report, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
