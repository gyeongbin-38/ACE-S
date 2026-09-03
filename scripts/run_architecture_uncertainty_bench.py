#!/usr/bin/env python3
"""Calibrate fail-closed uncertainty handling for architecture commitments."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from validate_architecture_uncertainty import validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "architecture-state-graph-valid-v0.1.json"


def remove_edge(g, src, rel, dst):
    g["traceability_edges"] = [e for e in g["traceability_edges"] if not (
        e.get("from") == src and e.get("relation") == rel and e.get("to") == dst
    )]


def main():
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = []

    cases.append(("accepted-intent-base", copy.deepcopy(base), True, set()))

    g = copy.deepcopy(base)
    g["unknowns"].append({"id":"unknown-deploy","type":"UNKNOWN","classification":"BLOCKING","evidence_status":"UNRESOLVED"})
    cases.append(("blocking-deployment-unknown", g, False, {"BLOCKING_UNKNOWN_UNRESOLVED"}))

    g = copy.deepcopy(base)
    g["unknowns"].append({"id":"unknown-owner","type":"UNKNOWN","classification":"RISK_BEARING","evidence_status":"UNRESOLVED"})
    cases.append(("unmitigated-risk-unknown", g, False, {"RISK_UNKNOWN_NO_MITIGATION","RISK_UNKNOWN_NO_REOPEN_CONDITION"}))

    g = copy.deepcopy(base)
    g["decisions"][0]["evidence_status"] = "UNRESOLVED"
    cases.append(("unresolved-high-lockin-decision", g, False, {"HIGH_LOCKIN_DECISION_UNRESOLVED"}))

    g = copy.deepcopy(base)
    g["decisions"][0]["evidence_status"] = "INFERRED"
    cases.append(("unsupported-high-lockin-inference", g, False, {"HIGH_LOCKIN_INFERENCE_UNSUPPORTED"}))

    g = copy.deepcopy(base)
    g["decisions"][0]["evidence_status"] = "INFERRED"
    g["traceability_edges"].append({"from":"ev-auth-test","relation":"SUPPORTS","to":"dec-store"})
    cases.append(("supported-high-lockin-inference", g, True, set()))

    g = copy.deepcopy(base)
    remove_edge(g, "asr-tenant-isolation", "DRIVES", "dec-store")
    cases.append(("high-lockin-without-driver", g, False, {"HIGH_LOCKIN_NO_TRACEABLE_DRIVER"}))

    rows = []
    failed = []
    for cid, graph, expected_pass, expected_errors in cases:
        result = validate(graph)
        actual = {x["code"] for x in result.get("issues", []) if x["severity"] == "error"}
        ok = result.get("gate_passed") == expected_pass and expected_errors.issubset(actual)
        row = {"id": cid, "passed": ok, "gate_passed": result.get("gate_passed"), "expected_errors": sorted(expected_errors), "actual_errors": sorted(actual)}
        rows.append(row)
        if not ok:
            failed.append({"row": row, "result": result})

    report = {
        "suite_id": "architecture-uncertainty-v0.1",
        "cases": len(rows),
        "passed": sum(1 for x in rows if x["passed"]),
        "rows": rows,
        "claim_boundary": "Authored uncertainty-governance fixtures only. They test abstention/commitment semantics, not LLM calibration or real-world evidence correctness.",
    }
    print(json.dumps(report, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
