#!/usr/bin/env python3
"""Aggregate paired runtime A/B traces while preserving per-task quality gates."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from compare_runtime_ab import compare
from validate_runtime_trace import load_trace


def weighted_pct(off: float, on: float) -> float | None:
    if off == 0:
        return 0.0 if on == 0 else None
    return 100.0 * (on / off - 1.0)


def run_suite(manifest_path: Path, quality_tolerance: float, material_improvement_pct: float) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("manifest.pairs must be a non-empty array")

    base = manifest_path.parent
    rows = []
    seen_tasks: set[str] = set()
    aggregate_metrics: dict[str, dict[str, float]] = {}

    for item in pairs:
        if not isinstance(item, dict) or not isinstance(item.get("off"), str) or not isinstance(item.get("on"), str):
            raise ValueError("each pair requires string off/on paths")
        result = compare(
            load_trace((base / item["off"]).resolve()),
            load_trace((base / item["on"]).resolve()),
            quality_tolerance=quality_tolerance,
            material_improvement_pct=material_improvement_pct,
        )
        task_id = result["task_id"]
        if task_id in seen_tasks:
            raise ValueError(f"duplicate task_id in suite: {task_id}")
        seen_tasks.add(task_id)
        rows.append(result)

        for metric, delta in result["metric_deltas"].items():
            if delta.get("status") not in {"measured_pair", "exact_trace_count_pair"}:
                continue
            agg = aggregate_metrics.setdefault(metric, {"off": 0.0, "on": 0.0, "pairs": 0.0})
            agg["off"] += float(delta["off"])
            agg["on"] += float(delta["on"])
            agg["pairs"] += 1.0

    quality_failures = [r["task_id"] for r in rows if not r["quality_gate_passed"]]
    pair_gate_failures = [r["task_id"] for r in rows if not r["paired_gate_passed"]]
    pass_regressions = [
        r["task_id"] for r in rows
        if r["quality"]["off_passed"] and not r["quality"]["on_passed"]
    ]
    quality_deltas = [
        float(r["quality"]["quality_score_delta"])
        for r in rows if r["quality"]["quality_score_delta"] is not None
    ]

    aggregate = {}
    suite_improvements = []
    for metric, vals in aggregate_metrics.items():
        change = weighted_pct(vals["off"], vals["on"])
        aggregate[metric] = {
            "paired_tasks": int(vals["pairs"]),
            "off_total": round(vals["off"], 6),
            "on_total": round(vals["on"], 6),
            "on_vs_off_change_pct": None if change is None else round(change, 6),
        }
        if change is not None and change <= -material_improvement_pct:
            suite_improvements.append(metric)

    # Quality First: no per-task quality regression may be hidden by aggregate efficiency.
    suite_quality_ok = not quality_failures and not pass_regressions
    suite_efficiency_ok = bool(suite_improvements)
    suite_pass = suite_quality_ok and suite_efficiency_ok

    return {
        "schema_version": "0.1",
        "suite_id": manifest.get("suite_id", manifest_path.stem),
        "tasks": len(rows),
        "suite_quality_gate_passed": suite_quality_ok,
        "suite_efficiency_gate_passed": suite_efficiency_ok,
        "suite_gate_passed": suite_pass,
        "quality_failure_task_ids": quality_failures,
        "pass_regression_task_ids": pass_regressions,
        "pair_gate_failure_task_ids": pair_gate_failures,
        "mean_quality_score_delta": None if not quality_deltas else round(statistics.fmean(quality_deltas), 6),
        "materially_improved_aggregate_metrics": suite_improvements,
        "aggregate_metric_deltas": aggregate,
        "pairs": [
            {
                "task_id": r["task_id"],
                "quality_gate_passed": r["quality_gate_passed"],
                "efficiency_gate_passed": r["efficiency_gate_passed"],
                "paired_gate_passed": r["paired_gate_passed"],
                "materially_improved_metrics": r["materially_improved_metrics"],
            }
            for r in rows
        ],
        "claim_boundary": "Suite gate prevents aggregate efficiency from hiding per-task quality regression. Fixture suites validate accounting semantics only; real performance claims require real-runtime paired traces.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--quality-tolerance", type=float, default=0.0)
    parser.add_argument("--material-improvement-pct", type=float, default=1.0)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    try:
        result = run_suite(args.manifest, args.quality_tolerance, args.material_improvement_pct)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "invalid_suite", "error": str(exc)}, indent=2))
        raise SystemExit(2)
    print(json.dumps(result, indent=2))
    if args.require_pass and not result["suite_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
