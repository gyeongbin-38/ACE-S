#!/usr/bin/env python3
"""Calibrate normalized architecture node/edge metrics and fragmentation semantics."""
from __future__ import annotations

import json

from architecture_structural_metrics import evaluate


def ref_graph():
    return {
        "nodes": [{"id":"api"},{"id":"domain"},{"id":"store"},{"id":"audit"}],
        "edges": [
            {"from":"api","relation":"CALLS","to":"domain"},
            {"from":"domain","relation":"WRITES","to":"store"},
            {"from":"domain","relation":"EMITS","to":"audit"},
        ],
    }


def aligned_node(cid, rid):
    return {"id": cid, "aligned_to": rid, "alignment_provenance": "FIXTURE"}


def close(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a-b) <= eps


def main():
    ref = ref_graph()
    cases = []

    exact = {
        "nodes": [aligned_node("n1","api"), aligned_node("n2","domain"), aligned_node("n3","store"), aligned_node("n4","audit")],
        "edges": [
            {"from":"n1","relation":"CALLS","to":"n2"},
            {"from":"n2","relation":"WRITES","to":"n3"},
            {"from":"n2","relation":"EMITS","to":"n4"},
        ],
    }
    cases.append(("exact", exact, {"node_f1":1.0,"edge_f1":1.0,"hallucination":0.0,"components":1}))

    # All entities are present, but one relation is missing and one is invented.
    # This calibrates the benchmark against the failure mode highlighted by R2ABench:
    # node extraction can look perfect while relation fidelity is materially worse.
    relation_gap = {
        "nodes": [aligned_node("n1","api"), aligned_node("n2","domain"), aligned_node("n3","store"), aligned_node("n4","audit")],
        "edges": [
            {"from":"n1","relation":"CALLS","to":"n2"},
            {"from":"n2","relation":"WRITES","to":"n3"},
            {"from":"n1","relation":"EMITS","to":"n4"},
        ],
    }
    cases.append(("perfect-nodes-broken-relations", relation_gap, {"node_f1":1.0,"edge_f1":2/3,"hallucination":1/3,"components":1}))

    fragmented = {
        "nodes": [
            aligned_node("n1","api"), aligned_node("n2","domain"), aligned_node("n3","store"),
            {"id":"ghost"},
        ],
        "edges": [
            {"from":"n1","relation":"CALLS","to":"n2"},
            {"from":"ghost","relation":"CALLS","to":"n3"},
        ],
    }
    # node TP=3 FP=1 FN=1 => P=R=.75, F1=.75
    # edge TP=1; ghost edge is unalignable FP=1; two reference edges are missing => F1=.4
    cases.append(("fragmented-hallucination", fragmented, {"node_f1":0.75,"edge_f1":0.4,"hallucination":0.5,"components":2}))

    rows, failed = [], []
    for cid, cand, expected in cases:
        result = evaluate(ref, cand)
        checks = {
            "node_f1": close(result["node"]["f1"], expected["node_f1"]),
            "edge_f1": close(result["edge"]["f1"], expected["edge_f1"]),
            "hallucination": close(result["edge_hallucination_rate"], expected["hallucination"]),
            "components": result["weak_component_count"] == expected["components"],
        }
        row = {
            "id": cid,
            "passed": all(checks.values()),
            "checks": checks,
            "node_f1": result["node"]["f1"],
            "edge_f1": result["edge"]["f1"],
            "edge_hallucination_rate": result["edge_hallucination_rate"],
            "weak_component_count": result["weak_component_count"],
        }
        rows.append(row)
        if not row["passed"]:
            failed.append({"row":row,"result":result})

    report = {
        "suite_id":"architecture-structural-metrics-v0.1",
        "cases":len(rows),
        "passed":sum(1 for x in rows if x["passed"]),
        "failed":len(failed),
        "rows":rows,
        "claim_boundary":"Authored normalized-graph fixtures test metric semantics only; they are not architecture-generation performance evidence.",
    }
    print(json.dumps(report, indent=2))
    if failed:
        print(json.dumps({"failures":failed}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
