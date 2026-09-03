#!/usr/bin/env python3
"""Validate uncertainty handling for architecture synthesis.

The goal is not to reward confidence. It prevents consequential decisions from
being finalized when their drivers depend on unresolved or unsupported inferred
context such as deployment, ownership, regulation, or operational constraints.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from validate_architecture_state_graph import NODE_COLLECTIONS, validate as validate_graph

UNKNOWN_CLASSES = {"BLOCKING", "RISK_BEARING", "REVERSIBLE"}
HIGH_LOCKIN = {"MIGRATABLE", "IRREVERSIBLE_OR_HIGH_LOCKIN"}


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def validate(graph: dict[str, Any]) -> dict[str, Any]:
    structural = validate_graph(graph)
    if not structural["gate_passed"]:
        return {
            "gate_passed": False,
            "issues": [issue("STRUCTURAL_GRAPH_INVALID", "graph", "run state-graph validation first")],
            "structural_errors": [x for x in structural["issues"] if x["severity"] == "error"],
            "claim_boundary": "Uncertainty gate was not evaluated because the graph itself is invalid.",
        }

    nodes = {}
    for collection, ntype in NODE_COLLECTIONS.items():
        for obj in graph.get(collection, []):
            if isinstance(obj, dict) and nonempty(obj.get("id")):
                nodes[obj["id"]] = (ntype, obj)

    incoming = defaultdict(list)
    for edge in graph.get("traceability_edges", []):
        if not isinstance(edge, dict):
            continue
        src, rel, dst = edge.get("from"), edge.get("relation"), edge.get("to")
        if src in nodes and dst in nodes:
            incoming[dst].append((rel, src))

    issues = []

    for i, obj in enumerate(graph.get("unknowns", [])):
        if not isinstance(obj, dict):
            continue
        cls = obj.get("classification")
        status = obj.get("evidence_status", "UNRESOLVED")
        if cls not in UNKNOWN_CLASSES:
            issues.append(issue("UNKNOWN_CLASSIFICATION_REQUIRED", f"unknowns[{i}].classification", "unknown must be BLOCKING, RISK_BEARING, or REVERSIBLE"))
            continue
        if cls == "BLOCKING" and status == "UNRESOLVED":
            issues.append(issue("BLOCKING_UNKNOWN_UNRESOLVED", f"unknowns[{i}]", "blocking architecture unknown must be resolved before finalization"))
        if cls == "RISK_BEARING" and status == "UNRESOLVED":
            if not nonempty(obj.get("mitigation")):
                issues.append(issue("RISK_UNKNOWN_NO_MITIGATION", f"unknowns[{i}].mitigation", "risk-bearing unresolved unknown needs mitigation"))
            if not nonempty(obj.get("reopen_condition")):
                issues.append(issue("RISK_UNKNOWN_NO_REOPEN_CONDITION", f"unknowns[{i}].reopen_condition", "risk-bearing unresolved unknown needs a reopen condition"))

    for i, obj in enumerate(graph.get("decisions", [])):
        if not isinstance(obj, dict) or obj.get("reversibility") not in HIGH_LOCKIN:
            continue
        did = obj.get("id")
        status = obj.get("evidence_status")
        if status == "UNRESOLVED":
            issues.append(issue("HIGH_LOCKIN_DECISION_UNRESOLVED", f"decisions[{i}]", "high-lock-in decision cannot be finalized as UNRESOLVED"))
        if status == "INFERRED":
            supporters = [
                src for rel, src in incoming.get(did, [])
                if rel == "SUPPORTS" and nodes[src][0] == "EVIDENCE"
            ]
            if not supporters:
                issues.append(issue("HIGH_LOCKIN_INFERENCE_UNSUPPORTED", f"decisions[{i}]", "inferred high-lock-in decision needs explicit supporting evidence"))
        drivers = [
            src for rel, src in incoming.get(did, [])
            if rel in {"DRIVES", "RESTRICTS"} and nodes[src][0] in {"REQUIREMENT", "ASR", "HARD_CONSTRAINT", "UNKNOWN"}
        ]
        if not drivers and not obj.get("drivers"):
            issues.append(issue("HIGH_LOCKIN_NO_TRACEABLE_DRIVER", f"decisions[{i}]", "high-lock-in decision needs a traceable driver"))

    errors = [x for x in issues if x["severity"] == "error"]
    return {
        "gate_passed": not errors,
        "error_count": len(errors),
        "issues": issues,
        "claim_boundary": "Deterministic uncertainty/commitment governance only. Passing does not prove that inferred evidence is correct or that a selected architecture is optimal.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("graph", type=Path)
    p.add_argument("--require-pass", action="store_true")
    args = p.parse_args()
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    result = validate(graph)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
