#!/usr/bin/env python3
"""Development v0.5.4: exhaustive subset boundary around the v0.5.3 winner.

The v0.5.3 winner was selected before this script existed with spans
(4, 8, 16, 24), max_windows=5, merge_gap=0. This bounded follow-up asks only:
1. can any non-empty subset of those scales pass with max_windows=4?
2. if max_windows=5 is necessary, can a strict subset preserve 14/14 with
   lower context cost?

No new span, retrieval rule, witness, selector coefficient, or semantic judge is
introduced. Development only; unseen suites remain unopened.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402

WINNER_SPANS = (4, 8, 16, 24)
MAX_WINDOWS = (4, 5)
MERGE_GAPS = (0, 1, 2)


def families():
    out = []
    for size in range(1, len(WINNER_SPANS) + 1):
        out.extend(itertools.combinations(WINNER_SPANS, size))
    return out


def key(row: dict) -> tuple:
    cfg = row["cfg"]
    return (
        row["worst_case_unique_source_lines"],
        row["mean_unique_source_lines"],
        row["actual_max_windows_emitted_per_task"],
        cfg["max_windows"],
        max(cfg["spans"]),
        cfg["merge_gap"],
        len(cfg["spans"]),
        tuple(cfg["spans"]),
    )


def compact(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "task_rows"}


def failed_tasks(row: dict) -> list[dict]:
    out=[]
    for task in row["task_rows"]:
        if task["frontier_hit"] and task["witness_hit"]:
            continue
        out.append({
            "task_id": task["task_id"],
            "frontier_hit": task["frontier_hit"],
            "failed_witnesses": [w for w in task["witness_rows"] if not w["hit"]],
        })
    return out


def main() -> None:
    manifest = multi.fixed.load_manifest()
    cached = multi.fixed.build_cache(manifest)
    configs = [
        multi.MultiScaleCfg(tuple(spans), max_windows, gap)
        for spans in families()
        for max_windows in MAX_WINDOWS
        for gap in MERGE_GAPS
    ]
    rows = [multi.evaluate_policy(cached, cfg) for cfg in configs]
    eligible = sorted((r for r in rows if r["hard_gate"]), key=key)
    eligible4 = sorted((r for r in rows if r["hard_gate"] and r["cfg"]["max_windows"] == 4), key=key)
    eligible5 = sorted((r for r in rows if r["hard_gate"] and r["cfg"]["max_windows"] == 5), key=key)
    best4_near = sorted(
        (r for r in rows if r["cfg"]["max_windows"] == 4),
        key=lambda r: (-r["witness_hits"], key(r)),
    )[0]
    selected = eligible[0] if eligible else None
    print(json.dumps({
        "experiment": "repo-behavior-witness-multiscale-subset-boundary-v0.5.4",
        "status": "development_only_post_winner_subset_boundary",
        "parent_winner": {"spans": [4,8,16,24], "max_windows": 5, "merge_gap": 0},
        "candidate_policies": len(rows),
        "families": len(families()),
        "eligible_total": len(eligible),
        "eligible_max_windows_4": len(eligible4),
        "eligible_max_windows_5": len(eligible5),
        "selected": compact(selected) if selected else None,
        "top_eligible": [compact(r) for r in eligible[:12]],
        "best_max_windows_4": {**compact(best4_near), "failures": failed_tasks(best4_near)},
        "claim_boundary": "Exhaustive non-empty subsets of the already-selected {4,8,16,24} scale family only. No new scale or selector parameter was introduced.",
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
