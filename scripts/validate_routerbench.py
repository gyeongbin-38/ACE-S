#!/usr/bin/env python3
"""Validate ACE-S RouterBench fixture structure.

This validates benchmark ground-truth data only. It does not run an LLM or
claim measured routing performance.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "routerbench-v0.1.json"

ACTIVATIONS = {"DIRECT", "ACTIVE", "UNCERTAIN"}
DOMAINS = {"GENERAL", "CODE", "LONG_DOCUMENT", "RESEARCH", "STATE"}
MODIFIERS = {"TEMPORAL", "EVIDENCE_CRITICAL", "PLAN_AWARE", "TOOL_DISCOVERY"}
FIDELITIES = {"INDEX", "SUMMARY", "EXTRACT", "RAW"}
BUCKETS = {"negative_control", "positive", "near_miss", "mixed_route", "ambiguous"}


def main() -> int:
    data = json.loads(BENCH.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    errors: list[str] = []
    ids: set[str] = set()

    if data.get("version") != "0.1":
        errors.append("version must be 0.1")
    if not cases:
        errors.append("cases must be non-empty")

    for idx, case in enumerate(cases):
        prefix = f"case[{idx}]"
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{prefix}: missing id")
        elif case_id in ids:
            errors.append(f"{prefix}: duplicate id {case_id}")
        else:
            ids.add(case_id)

        if case.get("bucket") not in BUCKETS:
            errors.append(f"{prefix}: invalid bucket {case.get('bucket')!r}")
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            errors.append(f"{prefix}: prompt must be non-empty")

        expected = case.get("expected")
        if not isinstance(expected, dict):
            errors.append(f"{prefix}: expected must be an object")
            continue

        if expected.get("activation") not in ACTIVATIONS:
            errors.append(f"{prefix}: invalid activation")
        if expected.get("primary_domain") not in DOMAINS:
            errors.append(f"{prefix}: invalid primary_domain")
        if expected.get("fidelity") not in FIDELITIES:
            errors.append(f"{prefix}: invalid fidelity")

        modifiers = expected.get("modifiers")
        if not isinstance(modifiers, list):
            errors.append(f"{prefix}: modifiers must be a list")
        else:
            unknown = set(modifiers) - MODIFIERS
            if unknown:
                errors.append(f"{prefix}: unknown modifiers {sorted(unknown)}")
            if len(modifiers) != len(set(modifiers)):
                errors.append(f"{prefix}: duplicate modifiers")

    required_buckets = {"negative_control", "near_miss", "mixed_route", "ambiguous"}
    present_buckets = {case.get("bucket") for case in cases}
    missing = required_buckets - present_buckets
    if missing:
        errors.append(f"missing required buckets: {sorted(missing)}")

    if errors:
        print("RouterBench validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"RouterBench OK: {len(cases)} fixtures, {len(present_buckets)} buckets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
