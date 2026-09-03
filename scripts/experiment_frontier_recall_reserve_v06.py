#!/usr/bin/env python3
"""v0.6 development experiment: reserve enough frontier capacity for recall.

Motivated by the opened Suite A GORM miss: the expected file is recall-rank 4,
while TOP_K=8 with exact_quota=5 leaves only three recall slots. This experiment
changes only exact-vs-recall frontier composition. Query terms, rankings,
TOP_K, behavior windows, and proof-authority logic are unchanged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import experiment_direct_proof_gate_v06 as proof_v06  # noqa: E402
import search_repo_behavior_witness_minimality_v05 as fixed  # noqa: E402

DEV = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-development-v0.5.json"
OPENED_A = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
QUOTAS = (3, 4, 5)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def eval_manifest(manifest: dict) -> dict:
    cached = fixed.build_cache(manifest)
    false_direct = 0
    hits = 0
    rows = []
    for item in cached:
        task = item["task"]
        expected = task["expected_file"]
        frontier = [r["path"] for r in item["frontier"]]
        hit = expected in frontier
        hits += int(hit)
        if item["proof_path"] is not None and item["proof_path"] != expected:
            false_direct += 1
        rows.append({
            "task_id": task["task_id"],
            "frontier_hit": hit,
            "frontier": frontier,
            "proof_path": item["proof_path"],
        })
    return {"tasks": len(rows), "frontier_hits": hits, "false_direct": false_direct, "rows": rows}


def main() -> None:
    dev = load(DEV)
    opened = load(OPENED_A)
    original_proof = fixed.old.direct_proof
    original_quota = fixed.EXACT_QUOTA
    fixed.old.direct_proof = proof_v06.safe_direct_proof
    results = []
    try:
        for quota in QUOTAS:
            fixed.EXACT_QUOTA = quota
            d = eval_manifest(dev)
            a = eval_manifest(opened)
            results.append({
                "exact_quota": quota,
                "recall_capacity_when_full": fixed.TOP_K - quota,
                "development14": d,
                "opened_suite_a6": a,
                "hard_gate": d["frontier_hits"] == 14 and a["frontier_hits"] == 6 and d["false_direct"] == 0 and a["false_direct"] == 0,
            })
    finally:
        fixed.old.direct_proof = original_proof
        fixed.EXACT_QUOTA = original_quota

    eligible = [r for r in results if r["hard_gate"]]
    # Preserve more exact capacity among passing policies; this is the smallest
    # deviation from the frozen quota=5 controller.
    selected = max(eligible, key=lambda r: r["exact_quota"]) if eligible else None
    print(json.dumps({
        "experiment": "frontier-recall-reserve-v0.6",
        "status": "development_only_after_suite_a_v01_opened",
        "top_k": fixed.TOP_K,
        "candidate_exact_quotas": list(QUOTAS),
        "results": results,
        "selected": None if selected is None else {
            "exact_quota": selected["exact_quota"],
            "recall_capacity_when_full": selected["recall_capacity_when_full"],
            "development14_frontier": selected["development14"]["frontier_hits"],
            "opened_suite_a6_frontier": selected["opened_suite_a6"]["frontier_hits"],
            "false_direct_total": selected["development14"]["false_direct"] + selected["opened_suite_a6"]["false_direct"],
        },
        "claim_boundary": "Frontier composition only. Opened Suite A v0.1 is development evidence; no unseen claim."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
