#!/usr/bin/env python3
"""Validate typed Architecture State Graph traceability and proof-path invariants.

This checker is deterministic and fail-closed for explicit graph obligations. It
also enforces canonical edge direction/type signatures so relation reversal is
caught instead of silently accepted. It is not an architecture-quality oracle.
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
    "deployment_units": "DEPLOYMENT_UNIT",
    "trust_enforcements": "TRUST_ENFORCEMENT",
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
ARCH_TYPES = {"COMPONENT", "BOUNDARY", "STATE", "FLOW", "INTERFACE", "DEPLOYMENT_UNIT", "DECISION"}
ANY_NON_EVIDENCE = set(NODE_COLLECTIONS.values()) - {"EVIDENCE"}
EDGE_SIGNATURES: dict[str, tuple[set[str], set[str]]] = {
    "SATISFIED_BY": ({"ASR"}, ARCH_TYPES),
    "RESTRICTS": ({"HARD_CONSTRAINT"}, {"DECISION", "BOUNDARY", "DEPLOYMENT_UNIT"}),
    "DRIVES": ({"REQUIREMENT", "ASR", "HARD_CONSTRAINT", "UNKNOWN"}, {"DECISION"}),
    "SELECTS": ({"DECISION"}, {"OPTION"}),
    "REJECTS": ({"DECISION"}, {"OPTION"}),
    "AFFECTS": ({"DECISION"}, ARCH_TYPES - {"DECISION"}),
    "SEPARATES": ({"BOUNDARY"}, {"COMPONENT"}),
    "OWNED_BY": ({"STATE"}, {"COMPONENT"}),
    "TRAVERSES": ({"FLOW"}, {"INTERFACE", "BOUNDARY"}),
    "READS": ({"FLOW"}, {"STATE"}),
    "WRITES": ({"FLOW"}, {"STATE"}),
    "ENFORCES": ({"TRUST_ENFORCEMENT", "COMPONENT", "INTERFACE"}, {"BOUNDARY"}),
    "ATTACKS": ({"SCENARIO"}, {"ASR", "DECISION", "FLOW", "BOUNDARY"}),
    "EXPOSED_BY": ({"RISK"}, {"SCENARIO"}),
    "VERIFIES": ({"FITNESS_CHECK"}, {"ASR", "DECISION", "BOUNDARY", "FLOW", "STATE"}),
    "PROVES": ({"PROOF_OBLIGATION"}, {"DECISION", "BOUNDARY", "FLOW", "STATE", "ASR"}),
    "SUPPORTS": ({"EVIDENCE"}, ANY_NON_EVIDENCE),
    "CONTRADICTS": ({"EVIDENCE"}, ANY_NON_EVIDENCE),
}


def nonempty(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def issue(code: str, path: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"code": code, "path": path, "message": message, "severity": severity}


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
            nid = obj.get("id")
            if not nonempty(nid):
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
        src_type, dst_type = nodes[src][0], nodes[dst][0]
        signature = EDGE_SIGNATURES.get(rel)
        if signature is None:
            issues.append(issue("UNKNOWN_RELATION", f"traceability_edges[{i}].relation", f"unknown canonical relation {rel}"))
        else:
            allowed_src, allowed_dst = signature
            if src_type not in allowed_src or dst_type not in allowed_dst:
                issues.append(issue(
                    "EDGE_DIRECTION_OR_TYPE_INVALID",
                    f"traceability_edges[{i}]",
                    f"{rel} requires {sorted(allowed_src)} -> {sorted(allowed_dst)}, got {src_type} -> {dst_type}",
                ))
        outgoing[src].append((rel, dst))
        incoming[dst].append((rel, src))

    def forward_reachable(start: str, relations: set[str], max_depth: int = 3) -> set[str]:
        q = deque([(start, 0)])
        seen = {start}
        reached: set[str] = set()
        while q:
            current, depth = q.popleft()
            if depth >= max_depth:
                continue
            for rel, nxt in outgoing.get(current, []):
                if rel not in relations or nxt in seen:
                    continue
                seen.add(nxt)
                reached.add(nxt)
                q.append((nxt, depth + 1))
        return reached

    # Critical ASR needs a traceable mechanism plus a fitness check that verifies
    # either the ASR itself or one of its mechanism nodes.
    for nid, (ntype, obj) in nodes.items():
        if ntype != "ASR" or obj.get("critical") is not True:
            continue
        mechanisms = {
            dst for rel, dst in outgoing.get(nid, [])
            if rel in {"SATISFIED_BY", "DRIVES"} and nodes[dst][0] in ARCH_TYPES
        }
        mechanisms |= {
            x for x in forward_reachable(nid, {"DRIVES", "AFFECTS"}, 2)
            if nodes[x][0] in ARCH_TYPES
        }
        if not mechanisms:
            issues.append(issue("CRITICAL_ASR_NO_MECHANISM_PATH", f"asrs[{nid}]", "critical ASR has no traceable architecture mechanism"))
        verify_targets = {nid} | mechanisms
        has_fitness = any(
            rel == "VERIFIES" and nodes[src][0] == "FITNESS_CHECK"
            for target in verify_targets
            for rel, src in incoming.get(target, [])
        )
        if not has_fitness:
            issues.append(issue("CRITICAL_ASR_NO_FITNESS_PATH", f"asrs[{nid}]", "critical ASR/mechanism has no verifying fitness check"))

    for nid, (ntype, obj) in nodes.items():
        if ntype != "STATE" or obj.get("mutable") is not True:
            continue
        owners = [dst for rel, dst in outgoing.get(nid, []) if rel == "OWNED_BY" and nodes[dst][0] == "COMPONENT"]
        if not owners and not nonempty(obj.get("multi_writer_protocol")):
            issues.append(issue("MUTABLE_STATE_NO_OWNER_PATH", f"state[{nid}]", "mutable state needs OWNED_BY or explicit multi_writer_protocol"))
        has_recovery_check = any(
            (rel == "VERIFIES" and nodes[src][0] == "FITNESS_CHECK") or
            (rel == "SUPPORTS" and nodes[src][0] == "EVIDENCE")
            for rel, src in incoming.get(nid, [])
        )
        if not nonempty(obj.get("recovery")) and not has_recovery_check:
            issues.append(issue("MUTABLE_STATE_NO_RECOVERY_PATH", f"state[{nid}]", "mutable state lacks recovery/rebuild path or verifying evidence"))

    for nid, (ntype, obj) in nodes.items():
        if ntype != "BOUNDARY" or obj.get("trust_boundary") is not True:
            continue
        enforcement = [
            src for rel, src in incoming.get(nid, [])
            if rel == "ENFORCES" and nodes[src][0] in {"TRUST_ENFORCEMENT", "COMPONENT", "INTERFACE"}
        ]
        if not enforcement and not nonempty(obj.get("enforcement")):
            issues.append(issue("TRUST_BOUNDARY_NO_ENFORCEMENT_PATH", f"boundaries[{nid}]", "trust boundary lacks enforcement point"))
        has_security_check = any(
            rel == "VERIFIES" and nodes[src][0] == "FITNESS_CHECK"
            for rel, src in incoming.get(nid, [])
        )
        if not has_security_check:
            issues.append(issue("TRUST_BOUNDARY_NO_SECURITY_CHECK", f"boundaries[{nid}]", "trust boundary lacks security verification path", "warning"))

    for nid, (ntype, obj) in nodes.items():
        if ntype != "DECISION" or obj.get("reversibility") not in HIGH_LOCKIN:
            continue
        selected = [dst for rel, dst in outgoing.get(nid, []) if rel == "SELECTS" and nodes[dst][0] == "OPTION"]
        affected = [dst for rel, dst in outgoing.get(nid, []) if rel == "AFFECTS" and nodes[dst][0] in (ARCH_TYPES - {"DECISION"})]
        if len(selected) != 1:
            issues.append(issue("HIGH_LOCKIN_SELECTION_INVALID", f"decisions[{nid}]", "high-lock-in decision must SELECT exactly one option"))
        if not affected:
            issues.append(issue("HIGH_LOCKIN_NO_AFFECTS_PATH", f"decisions[{nid}]", "high-lock-in decision has no AFFECTS edge"))
        if not nonempty(obj.get("kill_condition")):
            issues.append(issue("HIGH_LOCKIN_NO_KILL_CONDITION", f"decisions[{nid}]", "high-lock-in decision has no kill/reopen condition"))

    for nid, (ntype, obj) in nodes.items():
        if ntype == "EVIDENCE" and obj.get("derived") is True and obj.get("evidence_status") == "OBSERVED":
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
        "claim_boundary": "Deterministic graph integrity, canonical relation direction, and proof-path validation only; passing does not prove architecture optimality or mechanism quality.",
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
