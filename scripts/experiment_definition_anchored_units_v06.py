#!/usr/bin/env python3
"""v0.6 development experiment: add bounded definition-anchored Behavior Units.

Opened Suite A shows a recurrent failure mode where the correct file is in the
frontier and a satisfying sliding candidate exists, but the selected fixed
window clips the implementation body. This experiment leaves the existing
multi-scale sliding candidates intact and adds generic source-structure units:
for each recognized function/method/type definition, create a bounded forward
unit only when that unit contains query support.

No expected file, expected symbol, witness line, task id, or repository-specific
rule is used for candidate generation. Retrieval uses the independently tested
v0.6 repairs: explicit-authority direct proof and exact_quota=4.
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
DEF_CAPS = (0, 16, 24, 32, 48, 64)

ORIGINAL_CANDIDATE_FEATURES = multi.candidate_features


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def definition_augmented_features(cap: int):
    def candidate_features(lines, supports, spans):
        base_rows = list(ORIGINAL_CANDIDATE_FEATURES(lines, supports, spans))
        if cap <= 0:
            return base_rows

        by_interval = {(r["start"], r["end"]): dict(r) for r in base_rows}
        n = len(lines)
        for defline, text in enumerate(lines, 1):
            if not fixed.frontier_v02.is_definition_line(text):
                continue
            end = min(n, defline + cap - 1)
            # Candidate nomination remains query-grounded: a structural unit is
            # added only if some lexical support occurs inside the bounded body.
            if not any(supports[i - 1] for i in range(defline, end + 1)):
                continue
            per_term, structural, density, byte_cost = fixed.behavior_v03.window_features(
                lines, supports, defline, end
            )
            if not per_term:
                continue
            row = {
                "start": defline,
                "end": end,
                "span": cap,
                "per_term": per_term,
                "structural": structural,
                "density": density,
                "bytes": byte_cost,
                "unit_kind": "definition_forward",
            }
            old = by_interval.get((defline, end))
            if old is None:
                by_interval[(defline, end)] = row
            else:
                # Same visible interval: content-derived features are identical.
                # Keep a stable provenance label without changing scoring.
                old = dict(old)
                old["unit_kind"] = old.get("unit_kind", "sliding") + "+definition_forward"
                by_interval[(defline, end)] = old
        return sorted(by_interval.values(), key=lambda r: (r["start"], r["end"], r.get("span", 0)))
    return candidate_features


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
            for r in result["task_rows"]
            if not (r["frontier_hit"] and r["witness_hit"])
        ],
    }


def run_cap(cap: int) -> dict:
    old_candidates = multi.candidate_features
    old_proof = fixed.old.direct_proof
    old_quota = fixed.EXACT_QUOTA
    multi.candidate_features = definition_augmented_features(cap)
    fixed.old.direct_proof = proof_v06.safe_direct_proof
    fixed.EXACT_QUOTA = 4
    try:
        dev = eval_manifest(load(DEV))
        opened = eval_manifest(load(OPENED_A))
    finally:
        multi.candidate_features = old_candidates
        fixed.old.direct_proof = old_proof
        fixed.EXACT_QUOTA = old_quota
    hard_gate = (
        dev["frontier_hits"] == 14
        and dev["witness_hits"] == 14
        and dev["false_direct"] == 0
        and opened["frontier_hits"] == 6
        and opened["witness_hits"] == 6
        and opened["false_direct"] == 0
    )
    all_unique = [dev["worst_case_unique_source_lines"], opened["worst_case_unique_source_lines"]]
    weighted_mean = (
        dev["mean_unique_source_lines"] * 14 + opened["mean_unique_source_lines"] * 6
    ) / 20
    return {
        "definition_cap": cap,
        "hard_gate_20": hard_gate,
        "development14": dev,
        "opened_suite_a6": opened,
        "worst_case_unique_source_lines_20": max(all_unique),
        "mean_unique_source_lines_20": weighted_mean,
    }


def winner_key(row: dict) -> tuple:
    return (
        row["worst_case_unique_source_lines_20"],
        row["mean_unique_source_lines_20"],
        row["development14"]["actual_max_windows_emitted_per_task"],
        row["opened_suite_a6"]["actual_max_windows_emitted_per_task"],
        row["definition_cap"],
    )


def main() -> None:
    rows = [run_cap(cap) for cap in DEF_CAPS]
    eligible = sorted((r for r in rows if r["hard_gate_20"]), key=winner_key)
    selected = eligible[0] if eligible else None
    print(json.dumps({
        "experiment": "definition-anchored-behavior-units-v0.6",
        "status": "development_only_after_suite_a_v01_opened",
        "upstream_repairs": {
            "explicit_authority_direct_proof": True,
            "exact_quota": 4,
            "frontier_top_k": fixed.TOP_K,
        },
        "base_behavior_cfg": {"spans": [4,16,24], "max_windows": 5, "merge_gap": 0},
        "candidate_definition_caps": list(DEF_CAPS),
        "winner_rule": [
            "hard gate: dev14 14/14 + openedA6 6/6 + false_direct=0",
            "min worst-case unique source lines over 20 opened tasks",
            "min mean unique source lines over 20 opened tasks",
            "min emitted-window maxima",
            "min definition cap",
        ],
        "eligible": len(eligible),
        "selected": None if selected is None else {
            "definition_cap": selected["definition_cap"],
            "worst_case_unique_source_lines_20": selected["worst_case_unique_source_lines_20"],
            "mean_unique_source_lines_20": selected["mean_unique_source_lines_20"],
            "development14": selected["development14"],
            "opened_suite_a6": selected["opened_suite_a6"],
        },
        "results": rows,
        "claim_boundary": "All 20 tasks are opened development evidence. Any selected repair requires a fresh sealed Suite A v0.2 before generalization claims."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
