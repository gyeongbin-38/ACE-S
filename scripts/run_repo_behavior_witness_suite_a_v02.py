#!/usr/bin/env python3
"""Run fresh sealed Suite A v0.2 once with frozen v0.6.0 policy.

No policy search is available here. The manifest was sealed in a prior commit.
Any failure is preserved as unseen evaluation evidence and must not be tuned on
and then re-labelled as unseen.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import experiment_structural_closure_v06 as v06  # noqa: E402

SUITE = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.2.json"
CAP = 20


def main() -> None:
    manifest = json.loads(SUITE.read_text(encoding="utf-8"))
    if manifest.get("status") != "sealed_before_first_evaluation":
        raise RuntimeError("Suite A v0.2 is not sealed")
    tasks = manifest.get("tasks", [])
    if len(tasks) != 6:
        raise RuntimeError(f"expected 6 Suite A v0.2 tasks, got {len(tasks)}")

    cached = v06.build_cache(manifest)
    result = v06.evaluate(cached, CAP)
    out = {
        "experiment": "repo-behavior-witness-suite-a-v0.2",
        "status": "first_unseen_evaluation_result",
        "suite": str(SUITE.relative_to(ROOT)).replace("\\", "/"),
        "frozen_policy": {
            "safe_direct_proof": True,
            "frontier_top_k": v06.fixed.TOP_K,
            "exact_quota": v06.EXACT_QUOTA,
            "spans": list(v06.CFG.spans),
            "max_windows": v06.CFG.max_windows,
            "merge_gap": v06.CFG.merge_gap,
            "structural_closure_cap_lines": CAP,
        },
        "tasks": result["tasks"],
        "hard_gate": result["hard_gate"],
        "frontier_hits": result["frontier_hits"],
        "witness_hits": result["witness_hits"],
        "false_direct": result["false_direct"],
        "worst_case_unique_source_lines": result["worst_case_unique_source_lines"],
        "mean_unique_source_lines": result["mean_unique_source_lines"],
        "mean_extension_lines": result["mean_extension_lines"],
        "task_rows": result["task_rows"],
        "claim_boundary": (
            "Fresh Suite A v0.2 only. Policy v0.6.0 was frozen before this suite was constructed. "
            "No alternative quota, span, window budget, merge gap, proof rule, or closure cap is evaluated here."
        ),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
