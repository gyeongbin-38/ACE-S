#!/usr/bin/env python3
"""Development v0.5: pure Behavior Window minimality search.

The Behavior Witness manifest is frozen in a prior commit. This controller does
not use witness claim text, expected symbols, source blob hashes, or old anchor
strings to choose evidence. Those fields are labels/provenance only.

Hard gate:
- corrected expected file is in the frozen v0.2 retrieval frontier for all 14 tasks,
- no false-confident direct selection,
- every independently frozen witness region satisfies minimum_visible_lines.

Winner order, fixed before execution:
1. worst-case unique source lines exposed per task,
2. mean unique source lines exposed per task,
3. actual maximum windows emitted per task,
4. configured max_windows,
5. span,
6. merge_gap.

Development only. Do not use this result as unseen generalization evidence.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as rank_v03  # noqa: E402
import deterministic_repo_localization_v041 as rank_v041  # noqa: E402
import discover_repo_frontier_v02 as frontier_v02  # noqa: E402
import discover_repo_behavior_windows_v03 as behavior_v03  # noqa: E402
import run_repo_candidate_frontier_dev_v2 as old  # noqa: E402

WITNESS_MANIFEST = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-development-v0.5.json"
EXACT_QUOTA = 5
TOP_K = frontier_v02.TOP_K

# Search below the historical 8/3/2 setting and above it only far enough to
# diagnose a stricter witness if needed. Hybrid evidence is deliberately absent.
SPANS = (2, 4, 6, 8, 10, 12, 16, 20, 24)
MAX_WINDOWS = (1, 2, 3, 4)
MERGE_GAPS = (0, 1, 2)


def load_manifest() -> dict:
    data = json.loads(WITNESS_MANIFEST.read_text(encoding="utf-8"))
    if data.get("status") != "frozen_before_behavior_window_minimality_execution":
        raise RuntimeError("witness manifest is not marked frozen before controller execution")
    tasks = data.get("tasks", [])
    if len(tasks) != 14:
        raise RuntimeError(f"expected 14 frozen development tasks, got {len(tasks)}")
    return data


def git_blob_sha(repo: Path, path: str) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr[-1000:])
    return cp.stdout.strip()


def build_cache(manifest: dict) -> list[dict]:
    cached: list[dict] = []
    source_blobs = manifest["source_blobs"]
    for task in manifest["tasks"]:
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        actual_blob = git_blob_sha(repo, task["expected_file"])
        expected_blob = source_blobs[task["task_id"]]
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"source blob mismatch for {task['task_id']}: expected {expected_blob}, got {actual_blob}"
            )

        exact_terms = rank_v03.smart_query_terms(task["prompt"])
        exact_raw, exact_bytes = behavior_v03.decode_safe_grep(repo, exact_terms)
        exact_by = base.parse_hits(exact_raw, exact_terms)
        exact_ranked = rank_v041.certified_rank(exact_by, exact_terms)
        for i, row in enumerate(exact_ranked, 1):
            row["rank"] = i
        proof_path, proof_symbols = old.direct_proof(exact_by, task["prompt"])

        recall_terms = frontier_v02.prefix_terms(exact_terms)
        recall_raw, recall_bytes = behavior_v03.decode_safe_grep(repo, recall_terms)
        recall_by = base.parse_hits(recall_raw, recall_terms)
        recall_ranked = rank_v03.smart_rank_files(recall_by, recall_terms)
        for i, row in enumerate(recall_ranked, 1):
            row["rank"] = i

        if proof_path is not None:
            frontier = [row for row in exact_ranked if row["path"] == proof_path][:1]
        else:
            frontier = frontier_v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA)

        cached.append(
            {
                "task": task,
                "repo": repo,
                "terms": exact_terms + recall_terms,
                "frontier": frontier,
                "proof_path": proof_path,
                "proof_symbols": proof_symbols,
                "search_bytes": exact_bytes + recall_bytes,
            }
        )
    return cached


def visible_line_identities(cards: list[dict]) -> set[tuple[str, int]]:
    visible: set[tuple[str, int]] = set()
    for card in cards:
        path = card["path"]
        for record in card["records"]:
            visible.add((path, int(record["line"])))
    return visible


def witness_score(task: dict, visible: set[tuple[str, int]]) -> tuple[bool, list[dict]]:
    rows: list[dict] = []
    all_hit = True
    for witness_index, witness in enumerate(task["witnesses"], 1):
        overlap = sum(
            1
            for line in range(witness["start_line"], witness["end_line"] + 1)
            if (witness["path"], line) in visible
        )
        minimum = int(witness["minimum_visible_lines"])
        hit = overlap >= minimum
        all_hit = all_hit and hit
        rows.append(
            {
                "witness_index": witness_index,
                "path": witness["path"],
                "start_line": witness["start_line"],
                "end_line": witness["end_line"],
                "minimum_visible_lines": minimum,
                "visible_overlap_lines": overlap,
                "hit": hit,
            }
        )
    return all_hit, rows


def evaluate_policy(cached: list[dict], cfg: behavior_v03.WindowCfg) -> dict:
    task_rows: list[dict] = []
    false_direct = 0
    for item in cached:
        task = item["task"]
        expected_file = task["expected_file"]
        frontier_paths = [row["path"] for row in item["frontier"]]
        frontier_hit = expected_file in frontier_paths
        if item["proof_path"] is not None and item["proof_path"] != expected_file:
            false_direct += 1

        cards = [
            behavior_v03.behavior_card(item["repo"], row, item["terms"], cfg)
            for row in item["frontier"]
        ]
        visible = visible_line_identities(cards)
        witness_hit, witness_rows = witness_score(task, visible)
        unique_lines = len(visible)
        emitted_windows = sum(len(card["windows"]) for card in cards)
        per_card_max_windows = max((len(card["windows"]) for card in cards), default=0)

        task_rows.append(
            {
                "task_id": task["task_id"],
                "frontier_hit": frontier_hit,
                "witness_hit": witness_hit,
                "witness_rows": witness_rows,
                "unique_source_lines": unique_lines,
                "emitted_windows": emitted_windows,
                "max_windows_in_single_card": per_card_max_windows,
                "frontier": frontier_paths,
                "proof_path": item["proof_path"],
            }
        )

    frontier_hits = sum(1 for row in task_rows if row["frontier_hit"])
    witness_hits = sum(1 for row in task_rows if row["witness_hit"])
    unique_lines = [row["unique_source_lines"] for row in task_rows]
    emitted_windows = [row["emitted_windows"] for row in task_rows]
    hard_gate = (
        frontier_hits == len(task_rows)
        and witness_hits == len(task_rows)
        and false_direct == 0
    )
    return {
        "cfg": {
            "span": cfg.span,
            "max_windows": cfg.max_windows,
            "merge_gap": cfg.overlap_merge_gap,
        },
        "hard_gate": hard_gate,
        "frontier_hits": frontier_hits,
        "witness_hits": witness_hits,
        "false_direct": false_direct,
        "worst_case_unique_source_lines": max(unique_lines),
        "mean_unique_source_lines": statistics.fmean(unique_lines),
        "actual_max_windows_emitted_per_task": max(emitted_windows),
        "mean_windows_emitted_per_task": statistics.fmean(emitted_windows),
        "task_rows": task_rows,
    }


def winner_key(row: dict) -> tuple:
    cfg = row["cfg"]
    return (
        row["worst_case_unique_source_lines"],
        row["mean_unique_source_lines"],
        row["actual_max_windows_emitted_per_task"],
        cfg["max_windows"],
        cfg["span"],
        cfg["merge_gap"],
    )


def rejected_summary(row: dict) -> dict:
    failures = []
    for task_row in row["task_rows"]:
        if task_row["frontier_hit"] and task_row["witness_hit"]:
            continue
        failures.append(
            {
                "task_id": task_row["task_id"],
                "frontier_hit": task_row["frontier_hit"],
                "witness_hit": task_row["witness_hit"],
                "witness_rows": [w for w in task_row["witness_rows"] if not w["hit"]],
            }
        )
    return {
        "cfg": row["cfg"],
        "frontier_hits": row["frontier_hits"],
        "witness_hits": row["witness_hits"],
        "false_direct": row["false_direct"],
        "failures": failures,
    }


def compact_policy(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "task_rows"}


def main() -> None:
    manifest = load_manifest()
    cached = build_cache(manifest)
    configs = [
        behavior_v03.WindowCfg(span=span, max_windows=max_windows, overlap_merge_gap=merge_gap)
        for span in SPANS
        for max_windows in MAX_WINDOWS
        for merge_gap in MERGE_GAPS
    ]
    rows = [evaluate_policy(cached, cfg) for cfg in configs]
    eligible = sorted((row for row in rows if row["hard_gate"]), key=winner_key)
    selected = eligible[0] if eligible else None

    rejected = [rejected_summary(row) for row in rows if not row["hard_gate"]]
    # Keep lower-bound evidence compact: include every rejected policy whose
    # configured context is no larger than the selected policy on either span
    # or max_windows, plus all policies if no winner exists.
    if selected is not None:
        scfg = selected["cfg"]
        lower_bound = [
            row for row in rejected
            if row["cfg"]["span"] <= scfg["span"]
            and row["cfg"]["max_windows"] <= scfg["max_windows"]
        ]
    else:
        lower_bound = rejected

    out = {
        "experiment": "repo-behavior-witness-minimality-development-v0.5",
        "status": "development_only_frozen_witness_policy_search",
        "witness_manifest": str(WITNESS_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "tasks": len(cached),
        "candidate_policies": len(rows),
        "grid": {
            "spans": list(SPANS),
            "max_windows": list(MAX_WINDOWS),
            "merge_gaps": list(MERGE_GAPS),
        },
        "retrieval_policy": {"exact_quota": EXACT_QUOTA, "frontier_top_k": TOP_K},
        "winner_rule": [
            "hard_gate: frontier 14/14 + witness 14/14 + false_direct 0",
            "min worst_case_unique_source_lines",
            "min mean_unique_source_lines",
            "min actual_max_windows_emitted_per_task",
            "min configured max_windows",
            "min span",
            "min merge_gap",
        ],
        "eligible_policies": len(eligible),
        "selected": compact_policy(selected) if selected is not None else None,
        "selected_task_rows": selected["task_rows"] if selected is not None else [],
        "top_eligible": [compact_policy(row) for row in eligible[:12]],
        "lower_bound_counterexamples": lower_bound,
        "all_policy_metrics": [compact_policy(row) for row in rows],
        "claim_boundary": (
            "Already-observed development repositories only. Witness regions were frozen in a prior commit. "
            "Expected files and witness line ranges are post-hoc scoring labels; witness claims, expected symbols, "
            "and source blob SHAs are never inputs to evidence selection. Fresh sealed repositories are required "
            "before generalization claims."
        ),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
