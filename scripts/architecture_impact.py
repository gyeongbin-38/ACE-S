#!/usr/bin/env python3
"""Compute the minimal governed Architecture State Graph neighborhood to reopen.

The analyzer follows typed traceability semantics rather than reprocessing the
whole architecture. It is deterministic and conservative: it may return a
slightly larger neighborhood, but it must never infer absent relationships.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from validate_architecture_state_graph import NODE_COLLECTIONS, validate

INTENT_TYPES = {"REQUIREMENT", "ASR", "HARD_CONSTRAINT", "UNKNOWN"}
ARCH_TYPES = {"COMPONENT", "BOUNDARY", "STATE", "FLOW", "INTERFACE", "DEPLOYMENT_UNIT"}


def build_index(graph: dict[str, Any]):
    nodes: dict[str, tuple[str, dict[str, Any]]] = {}
    for collection, ntype in NODE_COLLECTIONS.items():
        for obj in graph.get(collection, []) if isinstance(graph.get(collection, []), list) else []:
            if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                nodes[obj["id"]] = (ntype, obj)
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    for edge in graph.get("traceability_edges", []):
        if not isinstance(edge, dict):
            continue
        src, rel, dst = edge.get("from"), edge.get("relation"), edge.get("to")
        if src in nodes and dst in nodes and isinstance(rel, str):
            outgoing[src].append((rel, dst))
            incoming[dst].append((rel, src))
    return nodes, outgoing, incoming


def impact(graph: dict[str, Any], changed_ids: list[str]) -> dict[str, Any]:
    validation = validate(graph)
    if not validation["gate_passed"]:
        return {
            "status": "invalid_graph",
            "changed_ids": changed_ids,
            "errors": [x for x in validation["issues"] if x["severity"] == "error"],
        }

    nodes, outgoing, incoming = build_index(graph)
    unknown = sorted(set(changed_ids) - set(nodes))
    if unknown:
        return {"status": "unknown_changed_node", "changed_ids": changed_ids, "unknown_ids": unknown}

    impacted = set(changed_ids)
    q = deque(changed_ids)

    def add(nid: str):
        if nid not in impacted:
            impacted.add(nid)
            q.append(nid)

    while q:
        nid = q.popleft()
        ntype = nodes[nid][0]

        # Evidence changes only affect the claims they explicitly support or contradict.
        if ntype == "EVIDENCE":
            for rel, dst in outgoing[nid]:
                if rel in {"SUPPORTS", "CONTRADICTS"}:
                    add(dst)

        # Changed intent drives only explicitly linked decisions/mechanisms.
        if ntype in INTENT_TYPES:
            for rel, dst in outgoing[nid]:
                if rel in {"DRIVES", "RESTRICTS", "SATISFIED_BY"}:
                    add(dst)

        # A changed option reopens decisions that selected/rejected it.
        if ntype == "OPTION":
            for rel, src in incoming[nid]:
                if rel in {"SELECTS", "REJECTS"} and nodes[src][0] == "DECISION":
                    add(src)

        # A changed architecture node reopens only decisions/ASRs explicitly tied to it.
        if ntype in ARCH_TYPES:
            for rel, src in incoming[nid]:
                if rel == "AFFECTS" and nodes[src][0] == "DECISION":
                    add(src)
                elif rel == "SATISFIED_BY" and nodes[src][0] == "ASR":
                    add(src)

        # A reopened decision brings its directly affected architecture neighborhood back in.
        if ntype == "DECISION":
            for rel, dst in outgoing[nid]:
                if rel == "AFFECTS" and nodes[dst][0] in ARCH_TYPES:
                    add(dst)

        # A changed scenario attacks only the explicitly named targets.
        if ntype == "SCENARIO":
            for rel, dst in outgoing[nid]:
                if rel == "ATTACKS":
                    add(dst)

    reopened_decisions = sorted(n for n in impacted if nodes[n][0] == "DECISION")
    impacted_architecture = sorted(n for n in impacted if nodes[n][0] in ARCH_TYPES)
    impacted_intent = sorted(n for n in impacted if nodes[n][0] in INTENT_TYPES)

    rerun_fitness = set()
    rerun_scenarios = set()
    reprove = set()
    for target in impacted:
        if nodes[target][0] == "FITNESS_CHECK":
            rerun_fitness.add(target)
        if nodes[target][0] == "SCENARIO":
            rerun_scenarios.add(target)
        if nodes[target][0] == "PROOF_OBLIGATION":
            reprove.add(target)
        for rel, src in incoming[target]:
            src_type = nodes[src][0]
            if rel == "VERIFIES" and src_type == "FITNESS_CHECK":
                rerun_fitness.add(src)
            elif rel == "ATTACKS" and src_type == "SCENARIO":
                rerun_scenarios.add(src)
            elif rel == "PROVES" and src_type == "PROOF_OBLIGATION":
                reprove.add(src)

    return {
        "status": "ok",
        "changed_ids": sorted(set(changed_ids)),
        "impacted_node_ids": sorted(impacted),
        "impacted_node_count": len(impacted),
        "total_node_count": len(nodes),
        "reopen_fraction": round(len(impacted) / len(nodes), 6) if nodes else 0.0,
        "reopened_decisions": reopened_decisions,
        "impacted_architecture": impacted_architecture,
        "impacted_intent": impacted_intent,
        "rerun_fitness_checks": sorted(rerun_fitness),
        "rerun_scenarios": sorted(rerun_scenarios),
        "reprove_obligations": sorted(reprove),
        "claim_boundary": "Typed dependency impact analysis only. It does not assert that unchanged nodes are semantically unaffected unless traceability edges are complete.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("graph", type=Path)
    p.add_argument("changed_ids", nargs="+")
    args = p.parse_args()
    graph = json.loads(args.graph.read_text(encoding="utf-8"))
    result = impact(graph, args.changed_ids)
    print(json.dumps(result, indent=2))
    if result.get("status") != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
