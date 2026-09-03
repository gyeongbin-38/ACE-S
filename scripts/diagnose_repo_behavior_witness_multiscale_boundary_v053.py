#!/usr/bin/env python3
"""Development diagnostic for the v0.5.3 multi-scale winner boundary.

This script does not search or select a new policy. It evaluates the frozen
winner and the immediately smaller window-budget variant under the same span
family and merge gap, then emits exact failing witness regions. Frozen witnesses
and controller equations are not modified.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402

CONFIGS = (
    multi.MultiScaleCfg((4, 8, 16, 24), 5, 0),
    multi.MultiScaleCfg((4, 8, 16, 24), 4, 0),
)


def main() -> None:
    manifest = multi.fixed.load_manifest()
    cached = multi.fixed.build_cache(manifest)
    rows = []
    for cfg in CONFIGS:
        result = multi.evaluate_policy(cached, cfg)
        failures = []
        for task in result["task_rows"]:
            failed_witnesses = [w for w in task["witness_rows"] if not w["hit"]]
            if not task["frontier_hit"] or failed_witnesses:
                failures.append(
                    {
                        "task_id": task["task_id"],
                        "frontier_hit": task["frontier_hit"],
                        "unique_source_lines": task["unique_source_lines"],
                        "emitted_windows": task["emitted_windows"],
                        "failed_witnesses": failed_witnesses,
                    }
                )
        rows.append(
            {
                "cfg": result["cfg"],
                "hard_gate": result["hard_gate"],
                "frontier_hits": result["frontier_hits"],
                "witness_hits": result["witness_hits"],
                "false_direct": result["false_direct"],
                "worst_case_unique_source_lines": result["worst_case_unique_source_lines"],
                "mean_unique_source_lines": result["mean_unique_source_lines"],
                "actual_max_windows_emitted_per_task": result["actual_max_windows_emitted_per_task"],
                "failures": failures,
            }
        )
    print(
        json.dumps(
            {
                "diagnostic": "repo-behavior-witness-multiscale-boundary-v0.5.3",
                "status": "development_only_no_policy_selection",
                "comparison": rows,
                "claim_boundary": "Same frozen 14-task witness manifest; diagnostic only. The 5-window winner was selected before this script existed.",
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
