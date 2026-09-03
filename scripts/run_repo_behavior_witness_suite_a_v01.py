#!/usr/bin/env python3
"""Run fresh sealed Suite A once with the frozen v0.5.4 policy.

This is evaluation, not policy search. The policy is fixed at spans=(4,16,24),
max_windows=5, merge_gap=0. Suite A failures must be recorded as failures; this
script exposes no alternative policy path and performs no tuning.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402

SUITE = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
FROZEN_CFG = multi.MultiScaleCfg((4, 16, 24), 5, 0)


def main() -> None:
    manifest = json.loads(SUITE.read_text(encoding="utf-8"))
    if manifest.get("status") != "sealed_before_first_evaluation":
        raise RuntimeError("Suite A is not sealed")
    tasks = manifest.get("tasks", [])
    if len(tasks) != 6:
        raise RuntimeError(f"expected 6 Suite A tasks, got {len(tasks)}")

    cached = multi.fixed.build_cache(manifest)
    result = multi.evaluate_policy(cached, FROZEN_CFG)
    out = {
        "experiment": "repo-behavior-witness-suite-a-v0.1",
        "status": "first_unseen_evaluation_result",
        "suite": str(SUITE.relative_to(ROOT)).replace("\\", "/"),
        "frozen_policy": result["cfg"],
        "tasks": len(tasks),
        "hard_gate": result["hard_gate"],
        "frontier_hits": result["frontier_hits"],
        "witness_hits": result["witness_hits"],
        "false_direct": result["false_direct"],
        "worst_case_unique_source_lines": result["worst_case_unique_source_lines"],
        "mean_unique_source_lines": result["mean_unique_source_lines"],
        "actual_max_windows_emitted_per_task": result["actual_max_windows_emitted_per_task"],
        "mean_windows_emitted_per_task": result["mean_windows_emitted_per_task"],
        "task_rows": result["task_rows"],
        "claim_boundary": (
            "Fresh Suite A only. Frozen policy was not searched or modified on these tasks. "
            "Any later policy change makes this suite development evidence and requires a new sealed suite."
        ),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
