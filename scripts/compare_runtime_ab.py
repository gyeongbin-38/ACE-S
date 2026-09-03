#!/usr/bin/env python3
"""Compare paired ACE-S OFF/ON runtime traces without mixing measurement classes.

This comparator is deliberately conservative:
- traces must share task_id;
- task_start.condition must be OFF vs ON;
- final quality must be non-inferior before any efficiency win counts;
- measured and estimated metrics are never silently mixed;
- unavailable metrics remain unavailable;
- synthetic/fixture traces are accounting tests, not performance claims.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from summarize_runtime_trace import summarize
from validate_runtime_trace import load_trace, validate

EFFICIENCY_METRICS = (
    "worker_visible_bytes",
    "worker_visible_tokens",
    "tool_latency_ms",
    "model_latency_ms",
    "wall_clock_ms",
    "sample_draws",
)
COUNT_METRICS = (
    "tool_rpc_calls",
    "unique_expensive_evaluations",
)


def condition(events: list[dict]) -> str:
    value = events[0].get("condition")
    if value not in {"OFF", "ON"}:
        raise ValueError("task_start.condition must be OFF or ON")
    return value


def pct_change(off: float, on: float) -> float | None:
    if off == 0:
        return 0.0 if on == 0 else None
    return 100.0 * (on / off - 1.0)


def measured_value(summary: dict, metric: str) -> float | None:
    values = summary.get("measured_metric_totals", {})
    value = values.get(metric)
    return None if value is None else float(value)


def quality_gate(off: dict, on: dict, tolerance: float) -> tuple[bool, dict]:
    off_pass = bool(off["passed"])
    on_pass = bool(on["passed"])
    off_q = off.get("quality_score")
    on_q = on.get("quality_score")

    pass_noninferior = (not off_pass) or on_pass
    score_noninferior = True
    score_delta = None
    if off_q is not None and on_q is not None:
        score_delta = float(on_q) - float(off_q)
        score_noninferior = score_delta >= -tolerance - 1e-12

    return pass_noninferior and score_noninferior, {
        "off_passed": off_pass,
        "on_passed": on_pass,
        "off_quality_score": off_q,
        "on_quality_score": on_q,
        "quality_score_delta": score_delta,
        "quality_tolerance": tolerance,
        "pass_noninferior": pass_noninferior,
        "score_noninferior": score_noninferior,
    }


def compare(off_events: list[dict], on_events: list[dict], *, quality_tolerance: float, material_improvement_pct: float) -> dict:
    validate(off_events)
    validate(on_events)
    if condition(off_events) != "OFF" or condition(on_events) != "ON":
        raise ValueError("first trace must be OFF and second trace must be ON")

    off = summarize(off_events)
    on = summarize(on_events)
    if off["task_id"] != on["task_id"]:
        raise ValueError("OFF and ON traces must share task_id")

    q_ok, q_detail = quality_gate(off, on, quality_tolerance)
    metric_deltas: dict[str, dict] = {}
    improvements: list[str] = []

    for metric in EFFICIENCY_METRICS:
        a = measured_value(off, metric)
        b = measured_value(on, metric)
        if a is None or b is None:
            metric_deltas[metric] = {"status": "unavailable_for_paired_measured_comparison"}
            continue
        change = pct_change(a, b)
        metric_deltas[metric] = {
            "status": "measured_pair",
            "off": a,
            "on": b,
            "on_vs_off_change_pct": None if change is None else round(change, 6),
        }
        if change is not None and change <= -material_improvement_pct:
            improvements.append(metric)

    for metric in COUNT_METRICS:
        a = float(off[metric])
        b = float(on[metric])
        change = pct_change(a, b)
        metric_deltas[metric] = {
            "status": "exact_trace_count_pair",
            "off": a,
            "on": b,
            "on_vs_off_change_pct": None if change is None else round(change, 6),
        }
        if change is not None and change <= -material_improvement_pct:
            improvements.append(metric)

    efficiency_ok = bool(improvements)
    passed = q_ok and efficiency_ok
    return {
        "schema_version": "0.1",
        "task_id": off["task_id"],
        "quality_gate_passed": q_ok,
        "quality": q_detail,
        "material_improvement_threshold_pct": material_improvement_pct,
        "materially_improved_metrics": improvements,
        "efficiency_gate_passed": efficiency_ok,
        "paired_gate_passed": passed,
        "metric_deltas": metric_deltas,
        "off_summary": off,
        "on_summary": on,
        "claim_boundary": "Paired trace accounting and quality gate only. A fixture pass is not an end-to-end model-performance claim; real claims require same-task real-runtime traces and scored final quality.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("off_trace", type=Path)
    parser.add_argument("on_trace", type=Path)
    parser.add_argument("--quality-tolerance", type=float, default=0.0)
    parser.add_argument("--material-improvement-pct", type=float, default=1.0)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    if args.quality_tolerance < 0 or not math.isfinite(args.quality_tolerance):
        raise SystemExit("--quality-tolerance must be finite and >= 0")
    if args.material_improvement_pct < 0 or not math.isfinite(args.material_improvement_pct):
        raise SystemExit("--material-improvement-pct must be finite and >= 0")

    try:
        result = compare(
            load_trace(args.off_trace),
            load_trace(args.on_trace),
            quality_tolerance=args.quality_tolerance,
            material_improvement_pct=args.material_improvement_pct,
        )
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "invalid_pair", "error": str(exc)}, indent=2))
        raise SystemExit(2)

    print(json.dumps(result, indent=2))
    if args.require_pass and not result["paired_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
