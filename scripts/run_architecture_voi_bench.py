#!/usr/bin/env python3
"""Calibrate conservative architecture VoI question selection."""
from __future__ import annotations

import json

from architecture_voi import evaluate_questions


def main():
    obj = {
        "directions": {"cost":"min", "availability":"max"},
        "candidates": [
            {"id":"A", "dimensions":{"cost":5, "availability":9}},
            {"id":"B", "dimensions":{"cost":None, "availability":None}},
            {"id":"C", "dimensions":{"cost":7, "availability":8}},
        ],
        "questions": [
            {
                "id":"measure-B-profile",
                "cost":2,
                "outcomes":[
                    {"assignments":[
                        {"candidate":"B","dimension":"cost","value":6},
                        {"candidate":"B","dimension":"availability","value":8}
                    ]},
                    {"assignments":[
                        {"candidate":"B","dimension":"cost","value":4},
                        {"candidate":"B","dimension":"availability","value":10}
                    ]},
                ],
            },
            {
                "id":"recheck-C-cost",
                "cost":1,
                "outcomes":[
                    {"assignments":[{"candidate":"C","dimension":"cost","value":6.5}]},
                    {"assignments":[{"candidate":"C","dimension":"cost","value":7.5}]},
                ],
            },
        ],
    }
    result = evaluate_questions(obj)

    # A and B are both on the initial frontier because B is materially unknown.
    # Measuring B's deployment profile is genuinely decision-changing in every
    # supplied outcome: B=(6,8) makes A dominate B, while B=(4,10) makes B
    # dominate A. Rechecking already-dominated C cannot resolve the A/B frontier.
    checks = {
        "baseline_frontier": set(result["baseline_frontier"]) == {"A","B"},
        "selected_high_value_question": result["selected_question"] == "measure-B-profile",
        "not_abstained": result["abstained"] is False,
    }
    by_id = {q["id"]: q for q in result["questions"]}
    checks["B_profile_guarantees_reduction"] = by_id["measure-B-profile"]["guaranteed_frontier_reduction"] == 1
    checks["C_question_no_guaranteed_reduction"] = by_id["recheck-C-cost"]["guaranteed_frontier_reduction"] == 0

    # If no supplied question can reduce the frontier in every outcome, the
    # conservative selector must abstain rather than invent probabilities.
    no_guarantee = {
        "directions": {"latency":"min"},
        "candidates": [
            {"id":"X", "dimensions":{"latency":10}},
            {"id":"Y", "dimensions":{"latency":None}},
        ],
        "questions": [{
            "id":"sample-Y-once",
            "cost":1,
            "outcomes":[
                {"assignments":[{"candidate":"Y","dimension":"latency","value":9}]},
                {"assignments":[{"candidate":"Y","dimension":"latency","value":10}]},
            ],
        }],
    }
    r2 = evaluate_questions(no_guarantee)
    checks["abstains_without_guaranteed_reduction"] = r2["abstained"] is True and r2["selected_question"] is None

    report = {
        "suite_id":"architecture-voi-v0.1",
        "passed":all(checks.values()),
        "checks":checks,
        "primary":result,
        "abstention_case":r2,
        "claim_boundary":"Authored finite-outcome fixtures validate question-selection semantics only; they do not establish real-world metric calibration or outcome completeness.",
    }
    print(json.dumps(report, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
