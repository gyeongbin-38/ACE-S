#!/usr/bin/env python3
"""Diagnose Echo/Axum/GORM behavior underexposure after Suite A v0.1 opened.

No selector or witness is modified. For each failed witness this reports whether
an existing frozen-scale candidate could satisfy the witness minimum and where
that candidate ranks before greedy coverage interactions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import experiment_direct_proof_gate_v06 as proof_v06  # noqa: E402
import search_repo_behavior_witness_minimality_v05 as fixed  # noqa: E402
import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402

SUITE = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
TARGETS = {"echo-raw-query-param-a03", "axum-path-extractor-a05", "gorm-statement-table-a06"}
CFG = multi.MultiScaleCfg((4, 16, 24), 5, 0)


def overlap(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0) + 1)


def initial_objective(w: dict) -> float:
    return sum(w["per_term"].values()) + 0.30 * w["structural"] + 0.20 * w["density"] - 0.00008 * w["bytes"]


def main() -> None:
    manifest = json.loads(SUITE.read_text(encoding="utf-8"))
    original_proof = fixed.old.direct_proof
    original_quota = fixed.EXACT_QUOTA
    fixed.old.direct_proof = proof_v06.safe_direct_proof
    fixed.EXACT_QUOTA = 4
    try:
        cached = fixed.build_cache(manifest)
    finally:
        fixed.old.direct_proof = original_proof
        fixed.EXACT_QUOTA = original_quota

    out = []
    for item in cached:
        task = item["task"]
        if task["task_id"] not in TARGETS:
            continue
        expected = task["expected_file"]
        expected_row = next(r for r in item["frontier"] if r["path"] == expected)
        lines, supports = multi.source_state(item["repo"], expected_row, item["terms"])
        candidates = multi.candidate_features(lines, supports, CFG.spans)
        ranked = sorted(
            candidates,
            key=lambda w: (-initial_objective(w), -sum(w["per_term"].values()), -w["structural"], w["bytes"], w["start"], w["span"]),
        )
        rank_by_interval = {(w["start"], w["end"], w["span"]): i for i, w in enumerate(ranked, 1)}
        card = multi.behavior_card(item["repo"], expected_row, item["terms"], CFG)
        selected = [(int(a), int(b)) for a, b in card["windows"]]
        visible = {(expected, int(r["line"])) for r in card["records"]}
        _hit, witness_rows = fixed.witness_score(task, visible)

        witness_diag = []
        for wi, witness in enumerate(task["witnesses"], 1):
            required = int(witness["minimum_visible_lines"])
            wr0, wr1 = int(witness["start_line"]), int(witness["end_line"])
            overlapping = []
            for w in candidates:
                ov = overlap(w["start"], w["end"], wr0, wr1)
                if ov <= 0:
                    continue
                overlapping.append({
                    "start": w["start"], "end": w["end"], "span": w["span"],
                    "overlap": ov,
                    "can_satisfy": ov >= required,
                    "initial_rank": rank_by_interval[(w["start"], w["end"], w["span"])],
                    "initial_objective": initial_objective(w),
                    "new_gain": sum(w["per_term"].values()),
                    "structural": w["structural"],
                })
            overlapping.sort(key=lambda r: (-r["can_satisfy"], -r["overlap"], r["initial_rank"], r["span"], r["start"]))
            selected_overlap = max((overlap(a,b,wr0,wr1) for a,b in selected), default=0)
            witness_diag.append({
                "witness_index": wi,
                "region": [wr0, wr1],
                "required": required,
                "selected_overlap_best_single_window": selected_overlap,
                "candidate_can_satisfy": any(r["can_satisfy"] for r in overlapping),
                "best_overlapping_candidates": overlapping[:8],
            })

        out.append({
            "task_id": task["task_id"],
            "expected_file": expected,
            "frontier": [r["path"] for r in item["frontier"]],
            "selected_windows": selected,
            "witness_rows": witness_rows,
            "witness_diagnostics": witness_diag,
        })

    print(json.dumps({
        "diagnostic": "behavior-underexposure-v0.6",
        "status": "development_after_suite_a_v01_opened",
        "cfg": {"spans": list(CFG.spans), "max_windows": CFG.max_windows, "merge_gap": CFG.merge_gap},
        "frontier_exact_quota_for_diagnostic": 4,
        "tasks": out,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
