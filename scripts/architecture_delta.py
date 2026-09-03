#!/usr/bin/env python3
"""Evaluate whether an architecture revision is causally local to changed intent.

The evaluator is reference-topology agnostic. It compares two valid Architecture
State Graphs and checks whether the revision stays inside the traceability
neighborhood opened by explicit requirement/ASR/constraint changes.

It is a governance/evaluation primitive, not an architecture-quality oracle.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from architecture_impact import impact
from validate_architecture_state_graph import NODE_COLLECTIONS, validate

HIGH_LOCKIN = {"MIGRATABLE", "IRREVERSIBLE_OR_HIGH_LOCKIN"}


def _nodes(graph: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    out: dict[str, tuple[str, dict[str, Any]]] = {}
    for collection, ntype in NODE_COLLECTIONS.items():
        values = graph.get(collection, [])
        if not isinstance(values, list):
            continue
        for obj in values:
            if isinstance(obj, dict) and isinstance(obj.get("id"), str):
                out[obj["id"]] = (ntype, obj)
    return out


def _edges(graph: dict[str, Any]) -> list[tuple[str, str, str]]:
    out = []
    for e in graph.get("traceability_edges", []):
        if not isinstance(e, dict):
            continue
        src, rel, dst = e.get("from"), e.get("relation"), e.get("to")
        if isinstance(src, str) and isinstance(rel, str) and isinstance(dst, str):
            out.append((src, rel, dst))
    return out


def _canonical(obj: dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _anchored_added_nodes(
    changed_graph: dict[str, Any],
    added: set[str],
    anchors: set[str],
) -> tuple[set[str], set[str]]:
    """Return (anchored, unanchored) added nodes.

    Added nodes may form a small new subgraph. A whole added connected component
    is accepted only when at least one member connects to an existing node in the
    governed impact closure (or to the changed intent itself).
    """
    adjacency: dict[str, set[str]] = defaultdict(set)
    external_links: dict[str, set[str]] = defaultdict(set)
    for src, _rel, dst in _edges(changed_graph):
        if src in added and dst in added:
            adjacency[src].add(dst)
            adjacency[dst].add(src)
        elif src in added:
            external_links[src].add(dst)
        elif dst in added:
            external_links[dst].add(src)

    seen: set[str] = set()
    anchored: set[str] = set()
    unanchored: set[str] = set()
    for start in sorted(added):
        if start in seen:
            continue
        comp: set[str] = set()
        q = deque([start])
        seen.add(start)
        while q:
            cur = q.popleft()
            comp.add(cur)
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        ext = set().union(*(external_links[n] for n in comp)) if comp else set()
        if ext & anchors:
            anchored |= comp
        else:
            unanchored |= comp
    return anchored, unanchored


def _high_lockin_ids(nodes: dict[str, tuple[str, dict[str, Any]]]) -> set[str]:
    return {
        nid for nid, (ntype, obj) in nodes.items()
        if ntype == "DECISION" and obj.get("reversibility") in HIGH_LOCKIN
    }


def evaluate_delta(
    base: dict[str, Any],
    changed: dict[str, Any],
    changed_intent_ids: list[str],
    change_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_valid = validate(base)
    changed_valid = validate(changed)
    if not base_valid.get("gate_passed") or not changed_valid.get("gate_passed"):
        return {
            "status": "invalid_graph",
            "base_gate_passed": base_valid.get("gate_passed"),
            "changed_gate_passed": changed_valid.get("gate_passed"),
            "base_errors": [x for x in base_valid.get("issues", []) if x.get("severity") == "error"],
            "changed_errors": [x for x in changed_valid.get("issues", []) if x.get("severity") == "error"],
        }

    closure = impact(base, changed_intent_ids)
    if closure.get("status") != "ok":
        return {"status": "impact_error", "impact": closure}

    base_nodes = _nodes(base)
    changed_nodes = _nodes(changed)
    base_ids, changed_ids = set(base_nodes), set(changed_nodes)
    shared = base_ids & changed_ids
    added = changed_ids - base_ids
    removed = base_ids - changed_ids
    modified = {
        nid for nid in shared
        if _canonical(base_nodes[nid][1]) != _canonical(changed_nodes[nid][1])
    }

    expected = set(closure["impacted_node_ids"])
    anchors = expected | set(changed_intent_ids)
    local_modified = modified & expected
    collateral_modified = modified - expected
    local_removed = removed & expected
    collateral_removed = removed - expected
    anchored_added, unanchored_added = _anchored_added_nodes(changed, added, anchors)

    actual_touched = modified | removed | added
    collateral = collateral_modified | collateral_removed | unanchored_added
    collateral_ratio = len(collateral) / len(actual_touched) if actual_touched else 0.0

    record = change_record or {}
    rerun_fit = set(record.get("rerun_fitness_checks", []))
    rerun_scen = set(record.get("rerun_scenarios", []))
    reprove = set(record.get("reprove_obligations", []))
    expected_fit = set(closure.get("rerun_fitness_checks", []))
    expected_scen = set(closure.get("rerun_scenarios", []))
    expected_proof = set(closure.get("reprove_obligations", []))

    missing_fit = expected_fit - rerun_fit
    missing_scen = expected_scen - rerun_scen
    missing_proof = expected_proof - reprove

    base_lockin = _high_lockin_ids(base_nodes)
    changed_lockin = _high_lockin_ids(changed_nodes)
    new_lockin = changed_lockin - base_lockin
    unanchored_new_lockin = new_lockin & unanchored_added

    issues = []
    if collateral_modified:
        issues.append({"code": "COLLATERAL_EXISTING_NODE_CHANGE", "ids": sorted(collateral_modified)})
    if collateral_removed:
        issues.append({"code": "COLLATERAL_EXISTING_NODE_REMOVAL", "ids": sorted(collateral_removed)})
    if unanchored_added:
        issues.append({"code": "UNANCHORED_NEW_ARCHITECTURE", "ids": sorted(unanchored_added)})
    if missing_fit:
        issues.append({"code": "MISSING_FITNESS_REVALIDATION", "ids": sorted(missing_fit)})
    if missing_scen:
        issues.append({"code": "MISSING_SCENARIO_RERUN", "ids": sorted(missing_scen)})
    if missing_proof:
        issues.append({"code": "MISSING_PROOF_REVALIDATION", "ids": sorted(missing_proof)})
    if unanchored_new_lockin:
        issues.append({"code": "UNANCHORED_LOCKIN_INFLATION", "ids": sorted(unanchored_new_lockin)})

    return {
        "status": "ok",
        "gate_passed": not issues,
        "changed_intent_ids": sorted(set(changed_intent_ids)),
        "expected_reopen_ids": sorted(expected),
        "modified_existing_ids": sorted(modified),
        "added_ids": sorted(added),
        "removed_ids": sorted(removed),
        "local_modified_ids": sorted(local_modified),
        "local_removed_ids": sorted(local_removed),
        "anchored_added_ids": sorted(anchored_added),
        "collateral_modified_ids": sorted(collateral_modified),
        "collateral_removed_ids": sorted(collateral_removed),
        "unanchored_added_ids": sorted(unanchored_added),
        "actual_touched_count": len(actual_touched),
        "collateral_change_ratio": round(collateral_ratio, 6),
        "expected_revalidation": {
            "fitness_checks": sorted(expected_fit),
            "scenarios": sorted(expected_scen),
            "proof_obligations": sorted(expected_proof),
        },
        "missing_revalidation": {
            "fitness_checks": sorted(missing_fit),
            "scenarios": sorted(missing_scen),
            "proof_obligations": sorted(missing_proof),
        },
        "new_high_lockin_decisions": sorted(new_lockin),
        "issues": issues,
        "claim_boundary": (
            "Counterfactual locality/governance only. Passing means the revision is traceably local "
            "to changed intent and reopens required checks; it does not prove the revised architecture "
            "is semantically correct or globally optimal."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("base", type=Path)
    p.add_argument("changed", type=Path)
    p.add_argument("changed_intent_ids", nargs="+")
    p.add_argument("--change-record", type=Path)
    p.add_argument("--require-pass", action="store_true")
    args = p.parse_args()
    base = json.loads(args.base.read_text(encoding="utf-8"))
    changed = json.loads(args.changed.read_text(encoding="utf-8"))
    record = json.loads(args.change_record.read_text(encoding="utf-8")) if args.change_record else None
    result = evaluate_delta(base, changed, args.changed_intent_ids, record)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result.get("gate_passed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
