#!/usr/bin/env python3
"""v0.6 development experiment: semantic novelty-aware overlap suppression.

Current multi-scale selection removes every candidate that overlaps a selected
window. Opened Suite A shows that an overlapping candidate may extend evidence
across a behavior boundary and carry query signals not yet covered. This test
keeps an overlapping candidate only when it still contains at least one
uncovered query-term support after the selected window is accepted.

Only overlap suppression changes. Objective coefficients, spans, max_windows,
merge gap, query terms, rankings, witness scoring, and TOP_K remain unchanged.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import experiment_direct_proof_gate_v06 as proof_v06  # noqa: E402
import search_repo_behavior_witness_minimality_v05 as fixed  # noqa: E402
import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402

DEV = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-development-v0.5.json"
OPENED_A = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
CFG = multi.MultiScaleCfg((4, 16, 24), 5, 0)


def novelty_choose_windows(lines, supports, cfg):
    remaining = list(multi.candidate_features(lines, supports, cfg.spans))
    selected = []
    covered: set[int] = set()
    while remaining and len(selected) < cfg.max_windows:
        best = None
        best_key = None
        for window in remaining:
            new_gain = sum(v for i, v in window["per_term"].items() if i not in covered)
            repeat_gain = sum(v for i, v in window["per_term"].items() if i in covered)
            objective = new_gain + 0.10 * repeat_gain + 0.30 * window["structural"] + 0.20 * window["density"] - 0.00008 * window["bytes"]
            key = (objective, new_gain, window["structural"], -window["bytes"], -window["start"])
            if best_key is None or key > best_key:
                best_key = key
                best = window
        if best is None or best_key is None or best_key[0] <= 0:
            break
        selected.append(best)
        covered.update(best["per_term"])

        next_remaining = []
        for window in remaining:
            if window is best:
                continue
            overlaps = (
                window["start"] <= best["end"] + cfg.merge_gap
                and best["start"] <= window["end"] + cfg.merge_gap
            )
            if overlaps:
                # Interval overlap alone is not enough to call evidence
                # redundant. Keep the candidate iff it still carries some
                # query signal not covered by selected evidence.
                has_uncovered = any(i not in covered for i in window["per_term"])
                if not has_uncovered:
                    continue
            next_remaining.append(window)
        remaining = next_remaining

    intervals = sorted((w["start"], w["end"]) for w in selected)
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + cfg.merge_gap:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(a, b) for a, b in merged]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def eval_manifest(manifest: dict) -> dict:
    cached = fixed.build_cache(manifest)
    result = multi.evaluate_policy(cached, CFG)
    return {
        "tasks": len(result["task_rows"]),
        "frontier_hits": result["frontier_hits"],
        "witness_hits": result["witness_hits"],
        "false_direct": result["false_direct"],
        "worst_case_unique_source_lines": result["worst_case_unique_source_lines"],
        "mean_unique_source_lines": result["mean_unique_source_lines"],
        "actual_max_windows_emitted_per_task": result["actual_max_windows_emitted_per_task"],
        "mean_windows_emitted_per_task": result["mean_windows_emitted_per_task"],
        "failures": [
            {
                "task_id": r["task_id"],
                "frontier_hit": r["frontier_hit"],
                "witness_hit": r["witness_hit"],
                "failed_witnesses": [w for w in r["witness_rows"] if not w["hit"]],
            }
            for r in result["task_rows"] if not (r["frontier_hit"] and r["witness_hit"])
        ],
    }


def run_variant(name: str, chooser) -> dict:
    old_choose = multi.choose_windows
    old_proof = fixed.old.direct_proof
    old_quota = fixed.EXACT_QUOTA
    multi.choose_windows = chooser
    fixed.old.direct_proof = proof_v06.safe_direct_proof
    fixed.EXACT_QUOTA = 4
    try:
        dev = eval_manifest(load(DEV))
        opened = eval_manifest(load(OPENED_A))
    finally:
        multi.choose_windows = old_choose
        fixed.old.direct_proof = old_proof
        fixed.EXACT_QUOTA = old_quota
    return {"variant": name, "development14": dev, "opened_suite_a6": opened}


def main() -> None:
    baseline = run_variant("strict_interval_overlap_suppression", multi.choose_windows)
    novelty = run_variant("keep_overlapping_candidate_if_uncovered_query_signal", novelty_choose_windows)
    for row in (baseline, novelty):
        d, a = row["development14"], row["opened_suite_a6"]
        row["hard_gate_20"] = (
            d["frontier_hits"] == 14 and d["witness_hits"] == 14 and d["false_direct"] == 0
            and a["frontier_hits"] == 6 and a["witness_hits"] == 6 and a["false_direct"] == 0
        )
        row["combined_mean_unique_source_lines"] = statistics.fmean([
            d["mean_unique_source_lines"], a["mean_unique_source_lines"]
        ])
    print(json.dumps({
        "experiment": "behavior-overlap-novelty-v0.6",
        "status": "development_only_after_suite_a_v01_opened",
        "upstream_repairs": {"safe_direct_proof": true, "exact_quota": 4, "top_k": fixed.TOP_K},
        "behavior_cfg": {"spans": [4,16,24], "max_windows": 5, "merge_gap": 0},
        "variants": [baseline, novelty],
        "claim_boundary": "Opened Suite A v0.1 is development evidence. This experiment tests one general overlap-redundancy rule only."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
