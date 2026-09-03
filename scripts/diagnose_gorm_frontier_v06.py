#!/usr/bin/env python3
"""Diagnose the opened Suite A GORM frontier miss without changing retrieval.

Outputs exact and prefix-recall terms/ranks, the current composed frontier, and
expected-file rank/score. Development-only diagnostic after Suite A v0.1 opened.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as rank_v03  # noqa: E402
import deterministic_repo_localization_v041 as rank_v041  # noqa: E402
import discover_repo_frontier_v02 as frontier_v02  # noqa: E402
import discover_repo_behavior_windows_v03 as behavior_v03  # noqa: E402

SUITE = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
TASK_ID = "gorm-statement-table-a06"
EXACT_QUOTA = 5


def compact(row: dict, rank: int) -> dict:
    return {
        "rank": rank,
        "path": row["path"],
        "score": row.get("score"),
        "exact_hits": row.get("exact_hits"),
        "matched_terms": row.get("matched_terms", []),
        "hit_bytes": row.get("hit_bytes"),
    }


def main() -> None:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    task = next(t for t in suite["tasks"] if t["task_id"] == TASK_ID)
    repo = base.ensure_repo(task["repository"], task["commit_sha"])

    exact_terms = rank_v03.smart_query_terms(task["prompt"])
    exact_raw, exact_bytes = behavior_v03.decode_safe_grep(repo, exact_terms)
    exact_by = base.parse_hits(exact_raw, exact_terms)
    exact_ranked = rank_v041.certified_rank(exact_by, exact_terms)
    for i, row in enumerate(exact_ranked, 1):
        row["rank"] = i

    recall_terms = frontier_v02.prefix_terms(exact_terms)
    recall_raw, recall_bytes = behavior_v03.decode_safe_grep(repo, recall_terms)
    recall_by = base.parse_hits(recall_raw, recall_terms)
    recall_ranked = rank_v03.smart_rank_files(recall_by, recall_terms)
    for i, row in enumerate(recall_ranked, 1):
        row["rank"] = i

    frontier = frontier_v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA)
    expected = task["expected_file"]
    exact_expected = next((compact(r, i) for i, r in enumerate(exact_ranked, 1) if r["path"] == expected), None)
    recall_expected = next((compact(r, i) for i, r in enumerate(recall_ranked, 1) if r["path"] == expected), None)

    out = {
        "diagnostic": "gorm-frontier-v0.6",
        "status": "development_after_suite_a_v01_opened",
        "task_id": TASK_ID,
        "prompt": task["prompt"],
        "expected_file": expected,
        "exact_terms": exact_terms,
        "recall_terms": recall_terms,
        "exact_search_bytes": exact_bytes,
        "recall_search_bytes": recall_bytes,
        "expected_exact": exact_expected,
        "expected_recall": recall_expected,
        "exact_top20": [compact(r, i) for i, r in enumerate(exact_ranked[:20], 1)],
        "recall_top20": [compact(r, i) for i, r in enumerate(recall_ranked[:20], 1)],
        "frontier": [r["path"] for r in frontier],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
