#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "benchmarks" / "results" / "live-github-replay-v0.2.csv"

EXPECTED = {
    "rows": 21,
    "stage1_exact": 13,
    "final_exact": 20,
    "canonical": 21,
    "round_sum": 29,
    "ace_repo_coverage": 7,
    "baseline_repo_coverage": 5,
    "ace_score_display": 90.2,
    "baseline_score_display": 72.9,
}


def as_bool(value: str) -> bool:
    value = value.strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"invalid boolean: {value!r}")
    return value == "true"


def score(exact_count: int, mean_rounds: float, covered_repos: int, total_rows: int, total_repos: int) -> float:
    exact_rate = 100.0 * exact_count / total_rows
    round_efficiency = 100.0 / mean_rounds
    coverage = 100.0 * covered_repos / total_repos
    return 0.60 * exact_rate + 0.25 * round_efficiency + 0.15 * coverage


def fail(message: str) -> None:
    print(f"FAILED: {message}")
    sys.exit(1)


def main() -> None:
    if not CSV_PATH.exists():
        fail(f"missing benchmark file: {CSV_PATH}")

    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    if len(rows) != EXPECTED["rows"]:
        fail(f"expected {EXPECTED['rows']} rows, found {len(rows)}")

    task_ids = [r["task_id"].strip() for r in rows]
    if len(task_ids) != len(set(task_ids)):
        fail("task_id values must be unique")
    if any(not task_id for task_id in task_ids):
        fail("task_id must not be blank")

    stage1 = 0
    final_exact = 0
    canonical = 0
    rounds: list[int] = []
    per_repo_stage1 = defaultdict(int)
    per_repo_final = defaultdict(int)
    per_repo_total = defaultdict(int)

    for row in rows:
        repo = row["repo"].strip()
        if not repo:
            fail(f"blank repo for {row['task_id']}")

        try:
            stage1_hit = as_bool(row["stage1_top5_exact"])
            final_hit = as_bool(row["final_exact"])
            canonical_hit = as_bool(row["canonical_target"])
            round_count = int(row["retrieval_rounds"])
        except (ValueError, TypeError) as exc:
            fail(f"invalid row {row['task_id']}: {exc}")

        if not (1 <= round_count <= 3):
            fail(f"retrieval_rounds must be in [1, 3] for {row['task_id']}")
        if final_hit and not canonical_hit:
            fail(f"exact hit must also be canonical for {row['task_id']}")

        stage1 += int(stage1_hit)
        final_exact += int(final_hit)
        canonical += int(canonical_hit)
        rounds.append(round_count)
        per_repo_total[repo] += 1
        per_repo_stage1[repo] += int(stage1_hit)
        per_repo_final[repo] += int(final_hit)

    if set(per_repo_total.values()) != {3}:
        fail(f"expected exactly 3 tasks per repo, got {dict(per_repo_total)}")

    if stage1 != EXPECTED["stage1_exact"]:
        fail(f"expected {EXPECTED['stage1_exact']} stage-1 hits, found {stage1}")
    if final_exact != EXPECTED["final_exact"]:
        fail(f"expected {EXPECTED['final_exact']} final exact hits, found {final_exact}")
    if canonical != EXPECTED["canonical"]:
        fail(f"expected {EXPECTED['canonical']} canonical hits, found {canonical}")
    if sum(rounds) != EXPECTED["round_sum"]:
        fail(f"expected round sum {EXPECTED['round_sum']}, found {sum(rounds)}")

    total_rows = len(rows)
    total_repos = len(per_repo_total)
    mean_rounds = sum(rounds) / total_rows

    ace_covered = sum(1 for repo in per_repo_total if per_repo_final[repo] >= 2)
    baseline_covered = sum(1 for repo in per_repo_total if per_repo_stage1[repo] >= 2)

    if ace_covered != EXPECTED["ace_repo_coverage"]:
        fail(f"expected ACE-S coverage {EXPECTED['ace_repo_coverage']}, found {ace_covered}")
    if baseline_covered != EXPECTED["baseline_repo_coverage"]:
        fail(f"expected baseline coverage {EXPECTED['baseline_repo_coverage']}, found {baseline_covered}")

    ace_score = score(final_exact, mean_rounds, ace_covered, total_rows, total_repos)
    baseline_score = score(stage1, 1.0, baseline_covered, total_rows, total_repos)

    # README/report headline values are shown to one decimal place.
    if round(ace_score, 1) != EXPECTED["ace_score_display"]:
        fail(
            f"ACE-S score drift: expected display {EXPECTED['ace_score_display']}, "
            f"got raw {ace_score:.6f} / display {round(ace_score, 1):.1f}"
        )
    if round(baseline_score, 1) != EXPECTED["baseline_score_display"]:
        fail(
            f"baseline score drift: expected display {EXPECTED['baseline_score_display']}, "
            f"got raw {baseline_score:.6f} / display {round(baseline_score, 1):.1f}"
        )

    print("OK: live benchmark invariants validated")
    print(f"  tasks:             {total_rows}")
    print(f"  repos:             {total_repos}")
    print(f"  baseline exact:    {stage1}/{total_rows}")
    print(f"  ACE-S exact:       {final_exact}/{total_rows}")
    print(f"  ACE-S canonical:   {canonical}/{total_rows}")
    print(f"  mean ACE-S rounds: {mean_rounds:.3f}")
    print(f"  baseline score:    {baseline_score:.6f} -> {baseline_score:.1f}/100")
    print(f"  ACE-S score:       {ace_score:.6f} -> {ace_score:.1f}/100")


if __name__ == "__main__":
    main()
