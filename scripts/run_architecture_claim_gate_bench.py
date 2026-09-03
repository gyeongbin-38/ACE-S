#!/usr/bin/env python3
"""Calibrate architecture evidence-claim promotion semantics."""
from __future__ import annotations

import copy
import json

from architecture_claim_gate import evaluate


def sealed_base():
    return {
        "external_sealed_projects": 20,
        "development_overlap_projects": 0,
        "method_and_evaluator_frozen_before_sealed": True,
        "same_model_settings_across_conditions": True,
        "edge_f1_delta_target_minus_direct": 0.08,
        "edge_f1_delta_ci_low": 0.02,
        "critical_asr_coverage_delta": 0.0,
        "hard_failure_rate_delta": -0.05,
        "reference_hidden_from_generator": True,
        "independent_model_families": 1,
        "direction_reproduced_across_model_families": False,
        "blind_human_reviews": 0,
        "human_preference_ci_low": 0.0,
        "inter_rater_agreement": 0.0,
        "compared_against_current_strong_baselines": False,
        "evaluation_artifacts_public": False,
        "claim_scope_matches_tested_scope": True,
    }


def main():
    cases = []

    cases.append(("mechanics-only", {}, "EXPERIMENTAL"))

    e = sealed_base()
    cases.append(("sealed-benchmark-improvement", e, "SEALED_BENCHMARK_IMPROVEMENT"))

    e = sealed_base()
    e["independent_model_families"] = 2
    e["direction_reproduced_across_model_families"] = True
    cases.append(("cross-model-replication", e, "CROSS_MODEL_REPLICATED_IMPROVEMENT"))

    e = copy.deepcopy(e)
    e.update({
        "blind_human_reviews": 72,
        "human_preference_ci_low": 0.58,
        "inter_rater_agreement": 0.52,
        "compared_against_current_strong_baselines": True,
        "evaluation_artifacts_public": True,
        "claim_scope_matches_tested_scope": True,
    })
    cases.append(("public-best-candidate", e, "PUBLIC_BEST_OR_SOTA_CANDIDATE"))

    e = copy.deepcopy(e)
    e["edge_f1_delta_ci_low"] = -0.01
    cases.append(("pretty-mean-uncertain-edge-gain", e, "EXPERIMENTAL"))

    e = copy.deepcopy(sealed_base())
    e["development_overlap_projects"] = 2
    cases.append(("contaminated-sealed-suite", e, "EXPERIMENTAL"))

    rows, failed = [], []
    for cid, evidence, expected in cases:
        result = evaluate(evidence)
        ok = result["achieved_level"] == expected
        row = {"id":cid,"passed":ok,"expected":expected,"actual":result["achieved_level"]}
        rows.append(row)
        if not ok:
            failed.append({"row":row,"result":result})

    report = {
        "suite_id":"architecture-claim-gate-v0.1",
        "cases":len(rows),
        "passed":sum(1 for x in rows if x["passed"]),
        "failed":len(failed),
        "rows":rows,
        "claim_boundary":"Authored evidence summaries test claim-gating semantics only; no architecture performance claim is produced by this benchmark.",
    }
    print(json.dumps(report, indent=2))
    if failed:
        print(json.dumps({"failures":failed}, indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
