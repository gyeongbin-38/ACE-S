#!/usr/bin/env python3
"""Summarize a validated ACE-S runtime trace without inventing unavailable metrics."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from validate_runtime_trace import load_trace, validate

METRICS = (
    "worker_visible_bytes", "worker_visible_tokens",
    "controller_only_bytes", "controller_only_tokens",
    "certificate_bytes", "certificate_tokens",
    "sample_draws", "wall_clock_ms", "tool_latency_ms", "model_latency_ms",
)


def summarize(events: list[dict]) -> dict:
    validation = validate(events)
    measured = defaultdict(float)
    estimated = defaultdict(float)
    statuses = Counter()
    unavailable = Counter()
    tool_calls: set[str] = set()
    cache_hits = cache_misses = 0
    expensive_evals: set[str] = set()
    certificates = 0
    certificates_with_provenance = 0
    full_exposures = certificate_exposures = 0

    for event in events:
        for name, spec in event.get("metrics", {}).items():
            status = spec["status"]
            statuses[(name, status)] += 1
            if status == "measured":
                measured[name] += float(spec["value"])
            elif status == "estimated":
                estimated[name] += float(spec["value"])
            else:
                unavailable[name] += 1
        typ = event["event_type"]
        if typ == "tool_call_start":
            tool_calls.add(event["call_id"])
        elif typ == "cache_hit":
            cache_hits += 1
        elif typ == "cache_miss":
            cache_misses += 1
        elif typ == "expensive_eval":
            expensive_evals.add(event["expensive_eval_id"])
        elif typ == "certificate_emitted":
            certificates += 1
            if event.get("provenance_refs"):
                certificates_with_provenance += 1
        elif typ == "worker_context_exposed":
            if event["representation"] == "certificate":
                certificate_exposures += 1
            else:
                full_exposures += 1

    end = events[-1]
    return {
        "schema_version": "0.1",
        "task_id": validation["task_id"],
        "passed": end["passed"],
        "quality_score": end.get("quality_score"),
        "event_count": len(events),
        "measured_metric_totals": {k: round(measured.get(k, 0.0), 6) for k in METRICS if k in measured},
        "estimated_metric_totals": {k: round(estimated.get(k, 0.0), 6) for k in METRICS if k in estimated},
        "unavailable_measurement_counts": {k: unavailable[k] for k in METRICS if unavailable[k]},
        "tool_rpc_calls": len(tool_calls),
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "unique_expensive_evaluations": len(expensive_evals),
        "certificates": certificates,
        "certificate_provenance_coverage_pct": 100.0 if certificates == 0 else round(100.0 * certificates_with_provenance / certificates, 3),
        "worker_full_exposures": full_exposures,
        "worker_certificate_exposures": certificate_exposures,
        "claim_boundary": "Trace accounting only. Efficiency is not a quality claim; paired OFF/ON interpretation requires same-task final-quality scoring.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    events = load_trace(args.trace)
    print(json.dumps(summarize(events), indent=2))


if __name__ == "__main__":
    main()
