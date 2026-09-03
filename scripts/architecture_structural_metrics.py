#!/usr/bin/env python3
"""Deterministic structural metrics for normalized architecture graphs.

Adapters are responsible for parsing source formats and producing explicit node
alignment. This evaluator never guesses semantic equivalence between node names.
Unaligned or invalidly aligned candidate nodes remain false positives.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 1.0 if fn == 0 else 0.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 6), "recall": round(r, 6), "f1": round(f, 6)}


def _reference_nodes(graph: dict[str, Any]) -> set[str]:
    return {
        n["id"] for n in graph.get("nodes", [])
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    }


def _candidate_nodes(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        n["id"]: n for n in graph.get("nodes", [])
        if isinstance(n, dict) and isinstance(n.get("id"), str)
    }


def _reference_edges(graph: dict[str, Any]) -> set[tuple[str, str, str]]:
    out = set()
    for e in graph.get("edges", []):
        if not isinstance(e, dict):
            continue
        src, dst = e.get("from"), e.get("to")
        if isinstance(src, str) and isinstance(dst, str):
            out.add((src, str(e.get("relation", "RELATES")), dst))
    return out


def _components(node_ids: set[str], edges: list[tuple[str, str]]) -> tuple[int, float]:
    if not node_ids:
        return 0, 1.0
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        if a in node_ids and b in node_ids:
            adj[a].add(b)
            adj[b].add(a)
    seen = set()
    sizes = []
    for start in sorted(node_ids):
        if start in seen:
            continue
        q = deque([start])
        seen.add(start)
        size = 0
        while q:
            cur = q.popleft()
            size += 1
            for nxt in adj[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        sizes.append(size)
    return len(sizes), max(sizes) / len(node_ids)


def evaluate(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    ref_nodes = _reference_nodes(reference)
    cand_nodes = _candidate_nodes(candidate)

    alignment: dict[str, str] = {}
    alignment_provenance: dict[str, str] = {}
    for cid, node in cand_nodes.items():
        rid = node.get("aligned_to")
        if isinstance(rid, str) and rid in ref_nodes:
            alignment[cid] = rid
            alignment_provenance[cid] = str(node.get("alignment_provenance", "UNSPECIFIED"))

    aligned_ref_ids = set(alignment.values())
    node_tp = len(aligned_ref_ids)
    node_fp = len(cand_nodes) - node_tp
    node_fn = len(ref_nodes - aligned_ref_ids)

    ref_edges = _reference_edges(reference)
    mapped_edges: set[tuple[str, str, str]] = set()
    raw_candidate_pairs: list[tuple[str, str]] = []
    unalignable_edge_count = 0
    for e in candidate.get("edges", []):
        if not isinstance(e, dict):
            continue
        src, dst = e.get("from"), e.get("to")
        if not (isinstance(src, str) and isinstance(dst, str)):
            continue
        raw_candidate_pairs.append((src, dst))
        if src not in alignment or dst not in alignment:
            unalignable_edge_count += 1
            continue
        mapped_edges.add((alignment[src], str(e.get("relation", "RELATES")), alignment[dst]))

    edge_tp = len(mapped_edges & ref_edges)
    edge_fp = len(mapped_edges - ref_edges) + unalignable_edge_count
    edge_fn = len(ref_edges - mapped_edges)
    edge_scores = _f1(edge_tp, edge_fp, edge_fn)
    candidate_edge_total = edge_tp + edge_fp
    edge_hallucination_rate = edge_fp / candidate_edge_total if candidate_edge_total else 0.0

    comp_count, largest_fraction = _components(set(cand_nodes), raw_candidate_pairs)
    provenance_counts: dict[str, int] = defaultdict(int)
    for p in alignment_provenance.values():
        provenance_counts[p] += 1

    return {
        "reference_node_count": len(ref_nodes),
        "candidate_node_count": len(cand_nodes),
        "reference_edge_count": len(ref_edges),
        "candidate_edge_count": len(candidate.get("edges", [])),
        "node": {**_f1(node_tp, node_fp, node_fn), "tp": node_tp, "fp": node_fp, "fn": node_fn},
        "edge": {**edge_scores, "tp": edge_tp, "fp": edge_fp, "fn": edge_fn},
        "edge_hallucination_rate": round(edge_hallucination_rate, 6),
        "alignment_coverage": round(len(alignment) / len(cand_nodes), 6) if cand_nodes else 1.0,
        "alignment_provenance_counts": dict(sorted(provenance_counts.items())),
        "weak_component_count": comp_count,
        "largest_component_fraction": round(largest_fraction, 6),
        "claim_boundary": (
            "Metrics are exact only with respect to the supplied normalized graph and explicit alignment. "
            "Semantic alignment quality is an upstream evaluator responsibility and must be reported separately."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("reference", type=Path)
    p.add_argument("candidate", type=Path)
    args = p.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(reference, candidate), indent=2))


if __name__ == "__main__":
    main()
