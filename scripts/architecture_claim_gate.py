#!/usr/bin/env python3
"""Fail closed on architecture-quality claim strength.

The gate separates mechanism tests, benchmark-scoped evidence, cross-model
replication, and public best/SOTA claims. It prevents authored fixtures or a
single favorable judge score from being promoted into a general quality claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

LEVELS = [
    "EXPERIMENTAL",
    "SEALED_BENCHMARK_IMPROVEMENT",
    "CROSS_MODEL_REPLICATED_IMPROVEMENT",
    "PUBLIC_BEST_OR_SOTA_CANDIDATE",
]


def b(v: Any) -> bool:
    return v is True


def num(obj: dict[str, Any], key: str, default: float = 0.0) -> float:
    v = obj.get(key, default)
    return float(v) if isinstance(v, (int, float)) else default


def evaluate(e: dict[str, Any]) -> dict[str, Any]:
    reasons: dict[str, list[str]] = {level: [] for level in LEVELS}

    sealed_ok = True
    if int(e.get("external_sealed_projects", 0) or 0) < 10:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("need >=10 external sealed projects")
    if int(e.get("development_overlap_projects", 0) or 0) != 0:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("development/sealed project overlap must be 0")
    if not b(e.get("method_and_evaluator_frozen_before_sealed")):
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("method/evaluator must be frozen before sealed execution")
    if not b(e.get("same_model_settings_across_conditions")):
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("conditions must use same model/settings")
    if num(e, "edge_f1_delta_target_minus_direct") <= 0:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("target must improve primary relation/edge F1")
    if num(e, "edge_f1_delta_ci_low") <= 0:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("edge-F1 improvement uncertainty interval must exclude non-improvement")
    if num(e, "critical_asr_coverage_delta") < 0:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("critical ASR coverage must not regress")
    if num(e, "hard_failure_rate_delta") > 0:
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("deterministic hard-failure rate must not increase")
    if not b(e.get("reference_hidden_from_generator")):
        sealed_ok = False; reasons["SEALED_BENCHMARK_IMPROVEMENT"].append("reference architecture must be hidden from generator")

    cross_ok = sealed_ok
    if int(e.get("independent_model_families", 0) or 0) < 2:
        cross_ok = False; reasons["CROSS_MODEL_REPLICATED_IMPROVEMENT"].append("need >=2 independent model families")
    if not b(e.get("direction_reproduced_across_model_families")):
        cross_ok = False; reasons["CROSS_MODEL_REPLICATED_IMPROVEMENT"].append("improvement direction must reproduce across model families")

    sota_ok = cross_ok
    if int(e.get("blind_human_reviews", 0) or 0) < 30:
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("need >=30 blind human review records")
    if num(e, "human_preference_ci_low") <= 0.5:
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("blind human preference CI must exceed 50%")
    if num(e, "inter_rater_agreement", 0.0) < 0.4:
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("inter-rater agreement must be at least 0.4")
    if not b(e.get("compared_against_current_strong_baselines")):
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("must compare against current strong baselines")
    if not b(e.get("evaluation_artifacts_public")):
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("evaluation artifacts must be public")
    if not b(e.get("claim_scope_matches_tested_scope")):
        sota_ok = False; reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"].append("claim scope must match tested scope")

    achieved = "EXPERIMENTAL"
    if sealed_ok:
        achieved = "SEALED_BENCHMARK_IMPROVEMENT"
    if cross_ok:
        achieved = "CROSS_MODEL_REPLICATED_IMPROVEMENT"
    if sota_ok:
        achieved = "PUBLIC_BEST_OR_SOTA_CANDIDATE"

    return {
        "achieved_level": achieved,
        "levels": {
            "EXPERIMENTAL": {"passed": True, "missing": []},
            "SEALED_BENCHMARK_IMPROVEMENT": {"passed": sealed_ok, "missing": reasons["SEALED_BENCHMARK_IMPROVEMENT"]},
            "CROSS_MODEL_REPLICATED_IMPROVEMENT": {
                "passed": cross_ok,
                "missing": reasons["SEALED_BENCHMARK_IMPROVEMENT"] + reasons["CROSS_MODEL_REPLICATED_IMPROVEMENT"],
            },
            "PUBLIC_BEST_OR_SOTA_CANDIDATE": {
                "passed": sota_ok,
                "missing": reasons["SEALED_BENCHMARK_IMPROVEMENT"] + reasons["CROSS_MODEL_REPLICATED_IMPROVEMENT"] + reasons["PUBLIC_BEST_OR_SOTA_CANDIDATE"],
            },
        },
        "claim_boundary": (
            "Passing the top gate permits a scoped public best/SOTA candidate claim; it does not prove universal optimality. "
            "Comparison scope, benchmark version, models, uncertainty, and limitations must still be stated."
        ),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("evidence", type=Path)
    p.add_argument("--require-level", choices=LEVELS)
    args = p.parse_args()
    obj = json.loads(args.evidence.read_text(encoding="utf-8"))
    result = evaluate(obj)
    print(json.dumps(result, indent=2))
    if args.require_level and not result["levels"][args.require_level]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
