#!/usr/bin/env python3
"""Diagnose why frozen Behavior Witness regions are or are not exposed.

Development-only diagnostic. This does not select a policy and does not mutate
witnesses. It distinguishes candidate-generation failures from greedy-selection
failures for a few bottleneck tasks under historical and maximum tested configs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_minimality_v05 as search  # noqa: E402

behavior = search.behavior_v03
TARGETS = {
    "chi-route-param-context-001",
    "k8s-current-context-evidence-001",
    "express-trust-proxy-ip-001",
    "requests-netrc-evidence-001",
}
CONFIGS = [
    behavior.WindowCfg(span=8, max_windows=3, overlap_merge_gap=2),
    behavior.WindowCfg(span=24, max_windows=4, overlap_merge_gap=0),
]


def first_step_candidates(lines: list[str], terms, span: int) -> list[dict]:
    supports = behavior.per_line_support(lines, terms)
    rows = []
    for start, end in behavior.candidate_windows(lines, supports, span):
        per_term, structural, density, byte_cost = behavior.window_features(
            lines, supports, start, end
        )
        if not per_term:
            continue
        objective = (
            sum(per_term.values())
            + 0.30 * structural
            + 0.20 * density
            - 0.00008 * byte_cost
        )
        rows.append(
            {
                "start": start,
                "end": end,
                "objective": objective,
                "new_gain": sum(per_term.values()),
                "structural": structural,
                "density": density,
                "bytes": byte_cost,
                "term_ids": sorted(per_term),
            }
        )
    rows.sort(
        key=lambda w: (
            -w["objective"],
            -w["new_gain"],
            -w["structural"],
            w["bytes"],
            w["start"],
        )
    )
    return rows


def overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]) + 1)


def main() -> None:
    manifest = search.load_manifest()
    cached = search.build_cache(manifest)
    output = []
    for item in cached:
        task = item["task"]
        if task["task_id"] not in TARGETS:
            continue
        expected_row = next(row for row in item["frontier"] if row["path"] == task["expected_file"])
        lines = (item["repo"] / task["expected_file"]).read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        term_labels = [term for term, _weight, _exactish in item["terms"]]
        task_out = {
            "task_id": task["task_id"],
            "expected_file": task["expected_file"],
            "terms": term_labels,
            "configs": [],
        }
        for cfg in CONFIGS:
            card = behavior.behavior_card(item["repo"], expected_row, item["terms"], cfg)
            visible = {(card["path"], int(r["line"])) for r in card["records"]}
            witness_hit, witness_rows = search.witness_score(task, visible)
            candidates = first_step_candidates(lines, item["terms"], cfg.span)
            witness_candidate_diagnostics = []
            for i, witness in enumerate(task["witnesses"], 1):
                region = (witness["start_line"], witness["end_line"])
                overlapping = [
                    (rank, row)
                    for rank, row in enumerate(candidates, 1)
                    if overlap((row["start"], row["end"]), region) > 0
                ]
                best = overlapping[0] if overlapping else None
                witness_candidate_diagnostics.append(
                    {
                        "witness_index": i,
                        "region": list(region),
                        "candidate_exists": bool(overlapping),
                        "best_first_step_rank": best[0] if best else None,
                        "best_candidate": best[1] if best else None,
                    }
                )
            selected_records = []
            for start, end in card["windows"]:
                selected_records.append(
                    {
                        "window": [start, end],
                        "text": [
                            {"line": n, "text": lines[n - 1]}
                            for n in range(start, min(end, start + 30) + 1)
                        ],
                    }
                )
            task_out["configs"].append(
                {
                    "cfg": {
                        "span": cfg.span,
                        "max_windows": cfg.max_windows,
                        "merge_gap": cfg.overlap_merge_gap,
                    },
                    "witness_hit": witness_hit,
                    "witness_rows": witness_rows,
                    "selected_windows": card["windows"],
                    "selected_records": selected_records,
                    "top_first_step_candidates": candidates[:10],
                    "witness_candidate_diagnostics": witness_candidate_diagnostics,
                }
            )
        output.append(task_out)
    print(json.dumps({"diagnostic": "repo-behavior-witness-v0.5", "tasks": output}, indent=2))


if __name__ == "__main__":
    main()
