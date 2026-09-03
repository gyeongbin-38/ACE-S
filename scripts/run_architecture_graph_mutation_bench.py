#!/usr/bin/env python3
"""Mutation benchmark for Architecture State Graph relation failures.

The benchmark starts from one valid graph and applies bounded structural
mutations. It measures whether deterministic validation catches the intended
relation/provenance failure. This is evaluator calibration, not evidence that an
LLM synthesis method is better.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from validate_architecture_state_graph import validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "benchmarks" / "architecture-state-graph-valid-v0.1.json"


def remove_edge(g, src, rel, dst):
    g["traceability_edges"] = [
        e for e in g["traceability_edges"]
        if not (e.get("from") == src and e.get("relation") == rel and e.get("to") == dst)
    ]


def mutations(base):
    cases = []

    g = copy.deepcopy(base)
    remove_edge(g, "asr-tenant-isolation", "SATISFIED_BY", "checkout-flow")
    remove_edge(g, "asr-tenant-isolation", "DRIVES", "dec-store")
    cases.append(("drop-asr-mechanism-edge", g, {"CRITICAL_ASR_NO_MECHANISM_PATH"}))

    g = copy.deepcopy(base)
    remove_edge(g, "fit-tenant", "VERIFIES", "asr-tenant-isolation")
    remove_edge(g, "fit-tenant", "VERIFIES", "checkout-flow")
    cases.append(("drop-asr-fitness-path", g, {"CRITICAL_ASR_NO_FITNESS_PATH"}))

    g = copy.deepcopy(base)
    remove_edge(g, "orders", "OWNED_BY", "store")
    cases.append(("drop-state-owner", g, {"MUTABLE_STATE_NO_OWNER_PATH"}))

    g = copy.deepcopy(base)
    for b in g["boundaries"]:
        if b["id"] == "tenant-boundary":
            b["enforcement"] = ""
    remove_edge(g, "api", "ENFORCES", "tenant-boundary")
    cases.append(("drop-trust-enforcement", g, {"TRUST_BOUNDARY_NO_ENFORCEMENT_PATH"}))

    g = copy.deepcopy(base)
    remove_edge(g, "dec-store", "SELECTS", "opt-single-store")
    cases.append(("drop-decision-selection", g, {"HIGH_LOCKIN_SELECTION_INVALID"}))

    g = copy.deepcopy(base)
    remove_edge(g, "dec-store", "AFFECTS", "orders")
    cases.append(("drop-decision-impact", g, {"HIGH_LOCKIN_NO_AFFECTS_PATH"}))

    g = copy.deepcopy(base)
    g["traceability_edges"].append({"from": "checkout-flow", "relation": "TRAVERSES", "to": "missing-interface"})
    cases.append(("dangling-relation", g, {"DANGLING_EDGE"}))

    g = copy.deepcopy(base)
    g["evidence"][0]["derived"] = True
    cases.append(("promote-derived-to-observed", g, {"DERIVED_EVIDENCE_MARKED_OBSERVED"}))

    g = copy.deepcopy(base)
    g["components"].append({"id": "api", "type": "COMPONENT", "evidence_status": "ACCEPTED_INTENT"})
    cases.append(("duplicate-stable-id", g, {"DUPLICATE_NODE_ID"}))

    g = copy.deepcopy(base)
    remove_edge(g, "fit-tenant", "VERIFIES", "tenant-boundary")
    g["traceability_edges"].append({"from": "tenant-boundary", "relation": "VERIFIES", "to": "fit-tenant"})
    cases.append(("reverse-canonical-edge", g, {"EDGE_DIRECTION_OR_TYPE_INVALID"}))

    return cases


def main():
    base = json.loads(FIXTURE.read_text(encoding="utf-8"))
    base_result = validate(base)
    rows = []
    failures = []

    if not base_result["gate_passed"]:
        failures.append({"id": "base-valid-graph", "reason": "base fixture failed", "issues": base_result["issues"]})

    for case_id, graph, expected_codes in mutations(base):
        result = validate(graph)
        actual = {x["code"] for x in result["issues"] if x["severity"] == "error"}
        caught = expected_codes.issubset(actual) and not result["gate_passed"]
        row = {
            "id": case_id,
            "caught": caught,
            "expected_error_codes": sorted(expected_codes),
            "actual_error_codes": sorted(actual),
        }
        rows.append(row)
        if not caught:
            failures.append(row)

    report = {
        "suite_id": "architecture-state-graph-mutation-v0.1",
        "base_graph_passed": base_result["gate_passed"],
        "mutations": len(rows),
        "caught": sum(1 for r in rows if r["caught"]),
        "mutation_detection_recall_pct": round(100.0 * sum(1 for r in rows if r["caught"]) / len(rows), 3),
        "rows": rows,
        "claim_boundary": "Authored structural mutations calibrate deterministic relation/provenance checks only; they do not measure LLM architecture generation quality.",
    }
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
