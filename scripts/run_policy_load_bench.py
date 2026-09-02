#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
import json

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "adaptive-context-engineering"
FIXTURE = ROOT / "benchmarks" / "policy-load-bench-v0.1.json"

KERNEL = "SKILL.md"
INDEX = "manifests/INDEX.md"
RESOLUTION = "references/resolution-ladder.md"

DOMAIN = {
    "GENERAL": (),
    "CODE": ("manifests/code.md", "references/coding.md"),
    "DOCUMENT": ("manifests/document.md", "references/long-document.md"),
    "RESEARCH": ("manifests/research.md", "references/research.md"),
    "STATE": ("manifests/state.md", "references/temporal.md"),
}

MODIFIER = {
    "TEMPORAL": ("manifests/temporal.md", "references/temporal.md"),
    "EVIDENCE": ("manifests/evidence.md", "references/evidence-and-provenance.md"),
    "TOOLS": ("manifests/tools.md", "references/tool-discovery.md"),
    "RETENTION": ("manifests/retention.md", "references/plan-aware.md"),
}

ALL_MANIFESTS = sorted({p for pair in DOMAIN.values() for p in pair[:1]} | {p for pair in MODIFIER.values() for p in pair[:1]})
ALL_SPECIALISTS = sorted({p for pair in DOMAIN.values() for p in pair[1:]} | {p for pair in MODIFIER.values() for p in pair[1:]} | {RESOLUTION})


def file_bytes(relative: str) -> int:
    return (SKILL / relative).stat().st_size


def bytes_for(paths: set[str]) -> int:
    return sum(file_bytes(path) for path in paths)


@dataclass
class Trace:
    loaded: list[str]

    def __init__(self) -> None:
        self.loaded = []

    def load(self, path: str) -> None:
        if path not in self.loaded:
            self.loaded.append(path)

    def load_domain_manifest(self, domain: str) -> None:
        pair = DOMAIN[domain]
        if pair:
            self.load(pair[0])

    def load_domain_specialist(self, domain: str) -> None:
        pair = DOMAIN[domain]
        if len(pair) > 1:
            self.load(pair[1])

    def load_domain(self, domain: str) -> None:
        self.load_domain_manifest(domain)
        self.load_domain_specialist(domain)

    def load_modifier(self, modifier: str) -> None:
        for path in MODIFIER[modifier]:
            self.load(path)


def minimum_paths(case: dict) -> set[str]:
    paths = {KERNEL}
    if case["activation"] == "DIRECT":
        return paths
    paths.add(INDEX)
    for path in DOMAIN[case["required_domain"]]:
        paths.add(path)
    for modifier in case["required_modifiers"]:
        paths.update(MODIFIER[modifier])
    if case.get("needs_resolution_policy"):
        paths.add(RESOLUTION)
    return paths


def first_candidate(case: dict) -> str:
    candidates = case.get("initial_candidates", [])
    return candidates[0] if candidates else "GENERAL"


def second_candidate(case: dict) -> str | None:
    candidates = case.get("initial_candidates", [])
    return candidates[1] if len(candidates) > 1 else None


def load_candidate_attempt(trace: Trace, candidate: str, case: dict, *, allow_specialist_on_wrong: bool) -> bool:
    required = case["required_domain"]
    trace.load_domain_manifest(candidate)
    if candidate == required:
        trace.load_domain_specialist(candidate)
        return True
    if allow_specialist_on_wrong:
        trace.load_domain_specialist(candidate)
    return False


def finish_required(trace: Trace, case: dict) -> None:
    for modifier in case["required_modifiers"]:
        trace.load_modifier(modifier)
    if case.get("needs_resolution_policy"):
        trace.load(RESOLUTION)


def simulate(case: dict, condition: str) -> dict:
    trace = Trace()
    trace.load(KERNEL)

    if case["activation"] == "DIRECT":
        success = True
        recovered = False
    else:
        trace.load(INDEX)
        required = case["required_domain"]
        first = first_candidate(case)
        second = second_candidate(case)
        wrong_requires_specialist = case.get("recovery_mode") == "specialist_no_progress"

        if condition == "A_full_load":
            for path in ALL_MANIFESTS:
                trace.load(path)
            for path in ALL_SPECIALISTS:
                trace.load(path)
            success = True
            recovered = first != required and second == required

        elif condition == "B_hard_single":
            matched = load_candidate_attempt(
                trace, first, case, allow_specialist_on_wrong=wrong_requires_specialist
            )
            # Hard-single has no lazy modifier expansion and no recovery.
            success = matched and not case["required_modifiers"] and not case.get("needs_resolution_policy")
            recovered = False

        elif condition == "C_progressive_no_recovery":
            matched = load_candidate_attempt(
                trace, first, case, allow_specialist_on_wrong=wrong_requires_specialist
            )
            if matched:
                finish_required(trace, case)
                success = True
            else:
                success = False
            recovered = False

        elif condition == "D_progressive_recovery":
            matched = load_candidate_attempt(
                trace, first, case, allow_specialist_on_wrong=wrong_requires_specialist
            )
            recovered = False
            if not matched and second is not None:
                matched = load_candidate_attempt(trace, second, case, allow_specialist_on_wrong=True)
                recovered = matched
            if matched:
                finish_required(trace, case)
                success = True
            else:
                success = False
        else:
            raise ValueError(condition)

    loaded_set = set(trace.loaded)
    minimum = minimum_paths(case)
    actual_bytes = bytes_for(loaded_set)
    minimum_bytes = bytes_for(minimum)
    irrelevant = loaded_set - minimum
    irrelevant_bytes = bytes_for(irrelevant)
    missing = minimum - loaded_set
    quality_adjusted_efficiency = (min(1.0, minimum_bytes / actual_bytes) if success else 0.0)

    return {
        "id": case["id"],
        "family": case["family"],
        "success": success,
        "recovered": recovered,
        "loaded_files": trace.loaded,
        "loaded_file_count": len(loaded_set),
        "actual_policy_bytes": actual_bytes,
        "oracle_minimum_bytes": minimum_bytes,
        "irrelevant_policy_bytes": irrelevant_bytes,
        "missing_required_files": sorted(missing),
        "quality_adjusted_efficiency": quality_adjusted_efficiency,
    }


def aggregate(cases: list[dict], rows: list[dict]) -> dict:
    active = [row for case, row in zip(cases, rows) if case["activation"] == "ACTIVE"]
    recoverable = [
        row
        for case, row in zip(cases, rows)
        if case["activation"] == "ACTIVE"
        and len(case.get("initial_candidates", [])) > 1
        and case["initial_candidates"][0] != case["required_domain"]
        and case["initial_candidates"][1] == case["required_domain"]
    ]

    success_rate = mean(row["success"] for row in rows)
    false_stop_rate = 1 - mean(row["success"] for row in active)
    recovery_rate = mean(row["success"] for row in recoverable) if recoverable else 1.0
    qa_efficiency = mean(row["quality_adjusted_efficiency"] for row in rows)
    total_actual = sum(row["actual_policy_bytes"] for row in rows)
    total_irrelevant = sum(row["irrelevant_policy_bytes"] for row in rows)
    irrelevant_rate = total_irrelevant / total_actual if total_actual else 0.0
    selective_purity = 1 - irrelevant_rate

    score = 100 * (
        0.45 * success_rate
        + 0.20 * qa_efficiency
        + 0.15 * selective_purity
        + 0.10 * recovery_rate
        + 0.10 * (1 - false_stop_rate)
    )

    family = {}
    for name in sorted({case["family"] for case in cases}):
        group = [row for row in rows if row["family"] == name]
        family[name] = {
            "n": len(group),
            "success_rate": round(100 * mean(row["success"] for row in group), 1),
            "mean_policy_bytes": round(mean(row["actual_policy_bytes"] for row in group), 1),
            "mean_loaded_files": round(mean(row["loaded_file_count"] for row in group), 2),
        }

    return {
        "n": len(rows),
        "selective_load_score": round(score, 1),
        "task_success_rate": round(100 * success_rate, 1),
        "recoverable_wrong_first_rate": round(100 * recovery_rate, 1),
        "false_stop_rate_active": round(100 * false_stop_rate, 1),
        "quality_adjusted_policy_efficiency": round(100 * qa_efficiency, 1),
        "irrelevant_policy_byte_rate": round(100 * irrelevant_rate, 1),
        "mean_policy_bytes": round(mean(row["actual_policy_bytes"] for row in rows), 1),
        "mean_loaded_files": round(mean(row["loaded_file_count"] for row in rows), 2),
        "max_loaded_files": max(row["loaded_file_count"] for row in rows),
        "families": family,
        "failures": [
            {"id": row["id"], "missing_required_files": row["missing_required_files"]}
            for row in rows
            if not row["success"]
        ],
    }


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases = data["cases"]
    conditions = [
        "A_full_load",
        "B_hard_single",
        "C_progressive_no_recovery",
        "D_progressive_recovery",
    ]

    output = {
        "experiment": "selective-policy-load-bench-v0.1",
        "fixture_count": len(cases),
        "important_caveat": "Controller-mechanics benchmark with oracle task requirements. It does not measure natural-language routing/model accuracy or end-to-end answer quality.",
        "score_formula": "45% task success + 20% quality-adjusted policy-byte efficiency + 15% selective purity + 10% recoverable wrong-first success + 10% active no-false-stop",
        "policy_sizes_bytes": {
            "kernel": file_bytes(KERNEL),
            "manifest_index": file_bytes(INDEX),
            "all_manifest_bytes": sum(file_bytes(p) for p in ALL_MANIFESTS),
            "all_specialist_bytes": sum(file_bytes(p) for p in ALL_SPECIALISTS),
        },
        "conditions": {},
    }

    for condition in conditions:
        rows = [simulate(case, condition) for case in cases]
        output["conditions"][condition] = aggregate(cases, rows)

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
