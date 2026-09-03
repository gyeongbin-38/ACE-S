#!/usr/bin/env python3
"""v0.6 development: bounded structural closure for Behavior Windows.

Inputs are development data only: the original 14-task witness set plus opened
Suite A v0.1. The already-supported v0.6 repairs are held fixed here:
- safe direct-proof authority gate,
- exact/recall frontier allocation 4/4 within TOP_K=8,
- Behavior Window policy spans=(4,16,24), max_windows=5, merge_gap=0.

Only evidence realization changes: when a selected window cuts through a
brace-delimited function/method definition, extend the window forward to the
matching closing brace if that closure is within a bounded cap. Expected files
and witness ranges are used only after evidence construction for scoring.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_minimality_v05 as fixed  # noqa: E402
import search_repo_behavior_witness_multiscale_v053 as multi  # noqa: E402
import experiment_direct_proof_gate_v06 as proof_v06  # noqa: E402

DEV = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-development-v0.5.json"
OPENED_A = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"
CFG = multi.MultiScaleCfg((4, 16, 24), 5, 0)
EXACT_QUOTA = 4
CAPS = (0, 4, 8, 12, 16, 20, 24, 32)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_cache(manifest: dict) -> list[dict]:
    cached = []
    source_blobs = manifest["source_blobs"]
    for task in manifest["tasks"]:
        repo = fixed.base.ensure_repo(task["repository"], task["commit_sha"])
        actual_blob = fixed.git_blob_sha(repo, task["expected_file"])
        expected_blob = source_blobs[task["task_id"]]
        if actual_blob != expected_blob:
            raise RuntimeError(f"source blob mismatch for {task['task_id']}: {actual_blob} != {expected_blob}")

        exact_terms = fixed.rank_v03.smart_query_terms(task["prompt"])
        exact_raw, exact_bytes = fixed.behavior_v03.decode_safe_grep(repo, exact_terms)
        exact_by = fixed.base.parse_hits(exact_raw, exact_terms)
        exact_ranked = fixed.rank_v041.certified_rank(exact_by, exact_terms)
        for i, row in enumerate(exact_ranked, 1):
            row["rank"] = i
        proof_path, proof_symbols = proof_v06.safe_direct_proof(exact_by, task["prompt"])

        recall_terms = fixed.frontier_v02.prefix_terms(exact_terms)
        recall_raw, recall_bytes = fixed.behavior_v03.decode_safe_grep(repo, recall_terms)
        recall_by = fixed.base.parse_hits(recall_raw, recall_terms)
        recall_ranked = fixed.rank_v03.smart_rank_files(recall_by, recall_terms)
        for i, row in enumerate(recall_ranked, 1):
            row["rank"] = i

        if proof_path is not None:
            frontier = [r for r in exact_ranked if r["path"] == proof_path][:1]
        else:
            frontier = fixed.frontier_v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA)

        cached.append({
            "task": task,
            "repo": repo,
            "terms": exact_terms + recall_terms,
            "frontier": frontier,
            "proof_path": proof_path,
            "proof_symbols": proof_symbols,
            "search_bytes": exact_bytes + recall_bytes,
        })
    return cached


def brace_delta(text: str) -> int:
    # Intentionally simple and language-neutral. Closure is bounded and only
    # activates on definition-like lines already recognized by the existing
    # structural detector. This is not a parser and cannot create direct proof.
    return text.count("{") - text.count("}")


def close_interval(lines: list[str], start: int, end: int, cap: int) -> tuple[int, int, int]:
    if cap <= 0 or end >= len(lines):
        return start, end, 0

    # Find the earliest definition inside the selected window whose block is
    # still open at the current window end. Earliest is deliberate: it closes
    # the behavior owner rather than a later nested helper.
    owner = None
    depth_at_end = 0
    for n in range(start, end + 1):
        text = lines[n - 1]
        if not fixed.frontier_v02.is_definition_line(text):
            continue
        if "{" not in text:
            continue
        depth = 0
        for k in range(n, end + 1):
            depth += brace_delta(lines[k - 1])
        if depth > 0:
            owner = n
            depth_at_end = depth
            break

    if owner is None:
        return start, end, 0

    depth = 0
    for n in range(owner, end + 1):
        depth += brace_delta(lines[n - 1])
    if depth <= 0:
        return start, end, 0

    limit = min(len(lines), end + cap)
    for n in range(end + 1, limit + 1):
        depth += brace_delta(lines[n - 1])
        if depth <= 0:
            return start, n, n - end
    return start, end, 0


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for start, end in sorted(intervals):
        if not out or start > out[-1][1]:
            out.append([start, end])
        else:
            out[-1][1] = max(out[-1][1], end)
    return [(a, b) for a, b in out]


def behavior_card(repo: Path, row: dict, terms, cap: int) -> dict:
    base_card = multi.behavior_card(repo, row, terms, CFG)
    path = row["path"]
    lines = (repo / path).read_text(encoding="utf-8", errors="replace").splitlines()
    closed = []
    extension_total = 0
    for start, end in base_card["windows"]:
        a, b, ext = close_interval(lines, start, end, cap)
        closed.append((a, b))
        extension_total += ext
    windows = merge(closed)
    records = []
    for wid, (start, end) in enumerate(windows, 1):
        for n in range(start, end + 1):
            records.append({"window": wid, "line": n, "text": lines[n - 1]})
    return {"path": path, "windows": windows, "records": records, "extension_lines": extension_total}


def evaluate(cached: list[dict], cap: int) -> dict:
    task_rows = []
    false_direct = 0
    for item in cached:
        task = item["task"]
        expected = task["expected_file"]
        frontier_paths = [r["path"] for r in item["frontier"]]
        frontier_hit = expected in frontier_paths
        if item["proof_path"] is not None and item["proof_path"] != expected:
            false_direct += 1

        cards = [behavior_card(item["repo"], r, item["terms"], cap) for r in item["frontier"]]
        visible = fixed.visible_line_identities(cards)
        witness_hit, witness_rows = fixed.witness_score(task, visible)
        unique_lines = len(visible)
        emitted_windows = sum(len(c["windows"]) for c in cards)
        extension_lines = sum(c["extension_lines"] for c in cards)
        task_rows.append({
            "task_id": task["task_id"],
            "frontier_hit": frontier_hit,
            "witness_hit": witness_hit,
            "witness_rows": witness_rows,
            "unique_source_lines": unique_lines,
            "emitted_windows": emitted_windows,
            "extension_lines": extension_lines,
            "frontier": frontier_paths,
            "proof_path": item["proof_path"],
        })

    n = len(task_rows)
    frontier_hits = sum(r["frontier_hit"] for r in task_rows)
    witness_hits = sum(r["witness_hit"] for r in task_rows)
    unique = [r["unique_source_lines"] for r in task_rows]
    extensions = [r["extension_lines"] for r in task_rows]
    return {
        "cap": cap,
        "tasks": n,
        "frontier_hits": frontier_hits,
        "witness_hits": witness_hits,
        "false_direct": false_direct,
        "hard_gate": frontier_hits == n and witness_hits == n and false_direct == 0,
        "worst_case_unique_source_lines": max(unique),
        "mean_unique_source_lines": statistics.fmean(unique),
        "mean_extension_lines": statistics.fmean(extensions),
        "task_rows": task_rows,
    }


def compact(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "task_rows"}


def main() -> None:
    dev = build_cache(load(DEV))
    opened = build_cache(load(OPENED_A))
    combined = dev + opened
    rows = [evaluate(combined, cap) for cap in CAPS]
    eligible = [r for r in rows if r["hard_gate"]]
    eligible.sort(key=lambda r: (r["worst_case_unique_source_lines"], r["mean_unique_source_lines"], r["cap"]))
    selected = eligible[0] if eligible else max(rows, key=lambda r: (r["witness_hits"], -r["worst_case_unique_source_lines"], -r["mean_unique_source_lines"]))

    print(json.dumps({
        "experiment": "behavior-window-structural-closure-v0.6",
        "status": "development_only_after_suite_a_v01_opened",
        "fixed_retrieval": {"exact_quota": EXACT_QUOTA, "top_k": fixed.TOP_K, "safe_direct_proof": True},
        "fixed_behavior_policy": {"spans": [4,16,24], "max_windows": 5, "merge_gap": 0},
        "caps": list(CAPS),
        "results": [compact(r) for r in rows],
        "selected": compact(selected),
        "selected_failures": [
            {"task_id": r["task_id"], "frontier_hit": r["frontier_hit"], "witness_rows": [w for w in r["witness_rows"] if not w["hit"]]}
            for r in selected["task_rows"] if not (r["frontier_hit"] and r["witness_hit"])
        ],
        "selected_task_rows": selected["task_rows"],
        "winner_rule": ["hard_gate on all 20 development tasks", "min worst unique lines", "min mean unique lines", "min closure cap"],
        "claim_boundary": "All 20 tasks are development evidence. Structural closure never sees expected files, symbols, or witness ranges during evidence construction. A fresh sealed suite is required after any v0.6 freeze."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
