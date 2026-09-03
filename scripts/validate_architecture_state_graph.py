#!/usr/bin/env python3
"""Validate typed Architecture State Graph traceability and proof-path invariants.

This checker is deterministic and fail-closed for explicit graph obligations. It
is not an architecture-quality oracle and does not judge whether the chosen
mechanisms are substantively good.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

NODE_COLLECTIONS = {
    "requirements": "REQUIREMENT",
    "asrs": "ASR",
    "hard_constraints": "HARD_CONSTRAINT",
    "non_goals": "NON_GOAL",
    "unknowns": "UNKNOWN",
    "components": "COMPONENT",
    "boundaries": "BOUNDARY",
    "state": "STATE",
    "interfaces": "INTERFACE",
    "critical_flows": "FLOW",
    "decisions": "DECISION",
    "options": "OPTION",
    "scenarios": "SCENARIO",
    "risks": "RISK",
    "proof_obligations": "PROOF_OBLIGATION",
    "fitness_checks": "FITNESS_CHECK",
    "evidence": "EVIDENCE",
}
ALLOWED_STATUS = {"OBSERVED", "ACCEPTED_INTENT", "INFERRED", "UNRESOLVED"}
HIGH_LOCKIN = {"MIGRATABLE", "IRREVERSIBLE_OR_HIGH_LOCKIN"}


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


def _node_id(obj: dict[str, Any]) -> str | None:
    v = obj.get("id")
    return v if nonempty(v) else None


def validate(graph: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    nodes: dict[str, tuple[str, dict[str, Any]]] = {}

    for collection, expected_type in NODE_COLLECTIONS.items():
        values = graph.get(collection, [])
        if not isinstance(values, list):
            issues.append(issue("COLLECTION_INVALID", collection, f"{collection} must be an array"))
            continue
        for i, obj in enumerate(values):
            if not isinstance(obj, dict):
                issues.append(issue("NODE_INVALID", f"{collection}[{i}]", "node must be object"))
                continue
            nid = _node_id(obj)
            if not nid:
                issues.append(issue("NODE_ID_REQUIRED", f"{collection}[{i}]", "stable id is required"))
                continue
            if nid in nodes:
                issues.append(issue("DUPLICATE_NODE_ID", f"{collection}[{i}].id", f"duplicate id {nid}"))
                continue
            declared = obj.get("type")
            if declared is not None and declared != expected_type:
                issues.append(issue("NODE_TYPE_MISMATCH", f"{collection}[{i}].type", f"expected {expected_type}, got {declared}"))
            status = obj.get("evidence_status")
            if status is not None and status not in ALLOWED_STATUS:
                issues.append(issue("EVIDENCE_STATUS_INVALID", f"{collection}[{i}].evidence_status", f"invalid evidence status {status}"))
            nodes[nid] = (expected_type, obj)

    edges = graph.get("traceability_edges", [])
    if not isinstance(edges, list):
        edges = []
        issues.append(issue("EDGES_INVALID", "traceability_edges", "traceability_edges must be an array"))

    outgoing: dict[str, list[tuple[str, str]]] = defaultdict(list)
    incoming: dict[str, list[tuple[str, str]]] = defaultdict(list)
    edge_seen: set[tuple[str, str, str]] = set()
    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(issue("EDGE_INVALID", f"traceability_edges[{i}]", "edge must be object"))
            continue
        src, rel, dst = edge.get("from"), edge.get("relation"), edge.get("to")
        if not (nonempty(src) and nonempty(rel) and nonempty(dst)):
            issues.append(issue("EDGE_FIELDS_REQUIRED", f"traceability_edges[{i}]", "from/relation/to are required"))
            continue
        if src not in nodes or dst not in nodes:
            issues.append(issue("DANGLING_EDGE", f"traceability_edges[{i}]", f"edge references unknown node: {src} -> {dst}"))
            continue
        key = (src, rel, dst)
        if key in edge_seen:
            issues.append(issue("DUPLICATE_EDGE", f"traceability_edges[{i}]", f"duplicate edge {key}", "warning"))
        edge_seen.add(key)
        outgoing[src].append((rel, dst))
        incoming[dst].append((rel, src))

    def has_path(start: str, target_types: set[str], relations: set[str] | None = None, max_depth: int = 4) -> bool:
        q = deque([(start, 0)])
        seen = {start}
        while q:
            current, depth = q.popleft()
            if depth >= max_depth:
                continue
            for rel, nxt in outgoing.get(current, []):
                if relations is not None and rel not in relations:
                    continue
                if nxt in seen:
                    continue
                if nodes[nxt][0] in target_types:
                    return True
                seen.add(nxt)
                q.append((nxt, depth + 1))
        return False

    # Critical ASR must reach an architecture mechanism and a fitness check.
    architecture_types = {"FLOW", "BOUNDARY", "STATE", "DECISION", "COMPONENT", "INTERFACE"}
    for nid, (ntype, obj) in nodes.items():
        if ntype == "ASR" and obj.get("critical") is True:
            if not has_path(nid, architecture_types, {"SATISFIED_BY", "RESTRICTS", "DRIVES"}, 3):
                issues.append(issue("CRITICAL_ASR_NO_MECHANISM_PATH", f"asrs[{nid}]", "critical ASR has no traceable architecture mechanism"))
            if not has_path(nid, {"FITNESS_CHECK"}, None, 5):
                issues.append(issue("CRITICAL_ASR_NO_FITNESS_PATH", f"asrs[{nid}]", "critical ASR cannot reach a fitness check"))

    # Mutable state must reach owner/protocol and recovery evidence/check.
    for nid, (ntype, obj) in nodes.items():
        if ntype != "STATE" or obj.get("mutable") is not True:
            continue
        owner_edges = [dst for rel, dst in outgoing.get(nid, []) if rel == "OWNED_BY" and nodes[dst][0] == "COMPONENT"]
        protocol = obj.get("multi_writer_protocol")
        if not owner_edges and not nonempty(protocol):
            issues.append(issue("MUTABLE_STATE_NO_OWNER_PATH", f"state[{nid}]", "mutable state needs OWNED_BY or explicit multi_writer_protocol"))
        recovery = obj.get("recovery")
        if not nonempty(recovery) and not has_path(nid, {"FITNESS_CHECK", "EVIDENCE"}, {"RECOVERED_BY", "VERIFIED_BY", "SUPPORTED_BY"}, 3):
            issues.append(issue("MUTABLE_STATE_NO_RECOVERY_PATH", f"state[{nid}]", "mutable state lacks recovery path"))

    # Trust boundary must have enforcement and a verification path.
    for nid, (ntype, obj) in nodes.items():
        if ntype != "BOUNDARY" or obj.get("trust_boundary") is not True:
            continue
        enforcement = [dst for rel, dst in incoming.get(nid, []) if rel == "ENFORCES" and nodes[dst][0] in {"COMPONENT", "INTERFACE"}]
        # Canonical graph may model dedicated TRUST_ENFORCEMENT node outside collection in future;
        # today enforcement components/interfaces are explicit and inspectable.
        if not enforcement and not nonempty(obj.get("enforcement")):
            issues.append(issue("TRUST_BOUNDARY_NO_ENFORCEMENT_PATH", f"boundaries[{nid}]", "trust boundary lacks enforcement point"))
        if not has_path(nid, {"FITNESS_CHECK"}, {"VERIFIED_BY", "PROTECTED_BY"}, 3):
            issues.append(issue("TRUST_BOUNDARY_NO_SECURITY_CHECK", f"boundaries[{nid}]", "trust boundary lacks security verification path", "warning"))

    # High-lock-in decisions need a selected option, architecture impact, and reopen condition.
    for nid, (ntype, obj) in nodes.items():
        if ntype != "DECISION" or obj.get("reversibility") not in HIGH_LOCKIN:
            continue
        selected = [dst for rel, dst in outgoing.get(nid, []) if rel == "SELECTS" and nodes[dst][0] == "OPTION"]
        affected = [dst for rel, dst in outgoing.get(nid, []) if rel == "AFFECTS" and nodes[dst][0] in architecture_types]
        if len(selected) != 1:
            issues.append(issue("HIGH_LOCKIN_SELECTION_INVALID", f"decisions[{nid}]", "high-lock-in decision must SELECT exactly one option"))
        if not affected:
            issues.append(issue("HIGH_LOCKIN_NO_AFFECTS_PATH", f"decisions[{nid}]", "high-lock-in decision has no AFFECTS edge"))
        if not nonempty(obj.get("kill_condition")):
            issues.append(issue("HIGH_LOCKIN_NO_KILL_CONDITION", f"decisions[{nid}]", "high-lock-in decision has no kill/reopen condition"))

    # Evidence may support claims, but inferred evidence cannot be silently marked observed.
    for nid, (ntype, obj) in nodes.items():
        if ntype != "EVIDENCE":
            continue
        if obj.get("derived") is True and obj.get("evidence_status") == "OBSERVED":
            issues.append(issue("DERIVED_EVIDENCE_MARKED_OBSERVED", f"evidence[{nid}]", "derived/inferred evidence cannot be OBSERVED"))

    errors = [x for x in issues if x["severity"] == "error"]
    warnings = [x for x in issues if x["severity"] == "warning"]
    return {
        "graph_id": graph.get("graph_id"),
        "gate_passed": not errors,
        "node_count": len(nodes),
        "edge_count": len(edge_seen),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
        "claim_boundary": "Deterministic graph integrity and proof-path validation only; passing does not prove architecture optimality or mechanism quality.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("graph", type=Path)
    p.add_argument("--require-pass", action="store_true")
    args = p.parse_args()
    obj = json.loads(args.graph.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise SystemExit("graph root must be object")
    result = validate(obj)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
