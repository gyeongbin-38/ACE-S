#!/usr/bin/env python3
"""Fast corrected-label diagnostic for the historical v0.3 Kubernetes miss.

Checks the original selected v0.3 behavior-window configuration against the
corrected frozen-source ground truth: config.go / writeCurrentContext.
Development diagnostic only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base
import deterministic_repo_localization_v03 as v03
import deterministic_repo_localization_v041 as v041
import discover_repo_frontier_v02 as v02
import discover_repo_behavior_windows_v03 as w
import run_repo_candidate_frontier_dev_v2 as old

TASKSET = ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.3-corrected.json"
CFG = w.WindowCfg(span=8, max_windows=3, overlap_merge_gap=2)
EXACT_QUOTA = 5


def main():
    task = next(t for t in json.loads(TASKSET.read_text(encoding="utf-8"))["tasks"] if t["task_id"] == "k8s-current-context-evidence-001")
    repo = base.ensure_repo(task["repository"], task["commit_sha"])
    exact_terms = v03.smart_query_terms(task["prompt"])
    exact_raw, _ = w.decode_safe_grep(repo, exact_terms)
    exact_by = base.parse_hits(exact_raw, exact_terms)
    exact_ranked = v041.certified_rank(exact_by, exact_terms)
    for i, r in enumerate(exact_ranked, 1): r["rank"] = i
    proof, _ = old.direct_proof(exact_by, task["prompt"])
    recall_terms = v02.prefix_terms(exact_terms)
    recall_raw, _ = w.decode_safe_grep(repo, recall_terms)
    recall_by = base.parse_hits(recall_raw, recall_terms)
    recall_ranked = v03.smart_rank_files(recall_by, recall_terms)
    for i, r in enumerate(recall_ranked, 1): r["rank"] = i
    frontier = ([r for r in exact_ranked if r["path"] == proof][:1] if proof else v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA))
    cards = [w.behavior_card(repo, r, exact_terms + recall_terms, CFG) for r in frontier]
    expected_cards = [c for c in cards if c["path"] == task["expected_file"]]
    anchor = task["expected_anchor"].lower()
    visible = any(anchor in "\n".join(x["text"] for x in c["records"]).lower() for c in expected_cards)
    print(json.dumps({
        "experiment": "k8s-corrected-behavior-v03-diagnostic",
        "task_id": task["task_id"],
        "expected_file": task["expected_file"],
        "expected_anchor": task["expected_anchor"],
        "frontier": [r["path"] for r in frontier],
        "frontier_hit": any(r["path"] == task["expected_file"] for r in frontier),
        "corrected_anchor_visible": visible,
        "historical_v03_cfg": {"span": 8, "max_windows": 3, "overlap_merge_gap": 2},
        "claim_boundary": "Seen-task corrected-label diagnostic only."
    }, indent=2))

if __name__ == "__main__":
    main()
