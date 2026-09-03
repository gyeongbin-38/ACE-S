#!/usr/bin/env python3
"""Development v0.4: hybrid evidence realization.

Motivation from observed development failures:
- coverage-oriented sparse lines preserved the Kubernetes clue but fragmented
  coherent Click/Axios behavior blocks,
- contiguous behavior windows repaired Click/Axios but one Kubernetes clue was
  displaced under the global window budget.

This experiment combines two generic evidence channels per candidate:
1) a tiny query-signal coverage capsule, and
2) one or two contiguous behavior windows.

The v0.2 dual-channel retrieval frontier is held fixed at exact_quota=5 and
TOP_K=8. Expected files/anchors are used only after construction for scoring.
All 14 tasks are already observed development data. A winning policy must be
frozen before any fresh repository/task suite is selected.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization_v041 as v041  # noqa: E402
import discover_repo_frontier_v02 as v02  # noqa: E402
import discover_repo_behavior_windows_v03 as v03w  # noqa: E402
import run_repo_candidate_frontier_dev_v2 as old  # noqa: E402

EXACT_QUOTA = 5


@dataclass(frozen=True)
class HybridCfg:
    coverage_seeds: int
    coverage_radius: int
    behavior_span: int
    behavior_windows: int
    merge_gap: int = 2


CONFIGS = [
    HybridCfg(seeds, radius, span, windows)
    for seeds in (1, 2, 3, 4, 5, 6)
    for radius in (0, 1)
    for span in (6, 8, 10)
    for windows in (1, 2)
]


def percentile(values: list[float], q: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def build_cache() -> list[dict]:
    cached = []
    for task in v02.load_tasks():
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        exact_terms = v03.smart_query_terms(task["prompt"])
        exact_raw, exact_bytes = v03w.decode_safe_grep(repo, exact_terms)
        exact_by = base.parse_hits(exact_raw, exact_terms)
        exact_ranked = v041.certified_rank(exact_by, exact_terms)
        for i, row in enumerate(exact_ranked, 1):
            row["rank"] = i
        proof_path, _symbols = old.direct_proof(exact_by, task["prompt"])

        recall_terms = v02.prefix_terms(exact_terms)
        recall_raw, recall_bytes = v03w.decode_safe_grep(repo, recall_terms)
        recall_by = base.parse_hits(recall_raw, recall_terms)
        recall_ranked = v03.smart_rank_files(recall_by, recall_terms)
        for i, row in enumerate(recall_ranked, 1):
            row["rank"] = i

        if proof_path is not None:
            frontier = [r for r in exact_ranked if r["path"] == proof_path][:1]
        else:
            frontier = v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA)

        cached.append({
            "task": task,
            "repo": repo,
            "terms": exact_terms + recall_terms,
            "frontier": frontier,
            "proof_path": proof_path,
            "search_bytes": exact_bytes + recall_bytes,
        })
    return cached


def coverage_lines(lines: list[str], terms: list[tuple[str, float, bool]], seeds: int, radius: int) -> set[int]:
    picked = v02.choose_seed_lines(lines, terms, seeds)
    wanted: set[int] = set()
    for seed in picked:
        for n in range(max(1, seed - radius), min(len(lines), seed + radius) + 1):
            wanted.add(n)
    return wanted


def hybrid_card(repo: Path, row: dict, terms: list[tuple[str, float, bool]], cfg: HybridCfg) -> dict:
    path = row["path"]
    lines = (repo / path).read_text(encoding="utf-8", errors="replace").splitlines()

    coverage = coverage_lines(lines, terms, cfg.coverage_seeds, cfg.coverage_radius)
    windows = v03w.choose_windows(
        lines,
        terms,
        v03w.WindowCfg(cfg.behavior_span, cfg.behavior_windows, cfg.merge_gap),
    )
    behavior: set[int] = set()
    for start, end in windows:
        behavior.update(range(start, end + 1))

    wanted = sorted(coverage | behavior)
    records = [
        {
            "line": n,
            "text": lines[n - 1],
            "coverage": n in coverage,
            "behavior": n in behavior,
        }
        for n in wanted
    ]
    return {
        "path": path,
        "behavior_windows": windows,
        "records": records,
    }


def main() -> None:
    cached = build_cache()
    rows = []
    for cfg in CONFIGS:
        frontier_hits = anchor_hits = false_direct = 0
        card_sizes = []
        task_rows = []
        for item in cached:
            task = item["task"]
            expected = task["expected_file"]
            anchor = task["expected_anchor"].lower()
            frontier_hit = any(r["path"] == expected for r in item["frontier"])
            frontier_hits += int(frontier_hit)
            if item["proof_path"] is not None and item["proof_path"] != expected:
                false_direct += 1

            cards = [hybrid_card(item["repo"], row, item["terms"], cfg) for row in item["frontier"]]
            expected_cards = [c for c in cards if c["path"] == expected]
            anchor_hit = any(
                anchor in "\n".join(record["text"] for record in card["records"]).lower()
                for card in expected_cards
            )
            anchor_hits += int(anchor_hit)
            card_bytes = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            card_sizes.append(card_bytes)
            task_rows.append({
                "task_id": task["task_id"],
                "frontier_hit": frontier_hit,
                "anchor_hit": anchor_hit,
                "card_bytes": card_bytes,
            })

        n = len(cached)
        rows.append({
            "cfg": asdict(cfg),
            "frontier_recall_pct": 100.0 * frontier_hits / n,
            "anchor_recall_pct": 100.0 * anchor_hits / n,
            "false_direct": false_direct,
            "mean_card_bytes": sum(card_sizes) / n,
            "p95_card_bytes": percentile(card_sizes, 0.95),
            "max_card_bytes": max(card_sizes),
            "task_rows": task_rows,
        })

    eligible = [
        row for row in rows
        if row["false_direct"] == 0
        and row["frontier_recall_pct"] == 100.0
        and row["anchor_recall_pct"] == 100.0
    ]
    eligible.sort(key=lambda r: (r["mean_card_bytes"], r["p95_card_bytes"], r["max_card_bytes"]))
    best = eligible[0] if eligible else max(rows, key=lambda r: (r["anchor_recall_pct"], -r["mean_card_bytes"]))

    output = {
        "experiment": "repo-hybrid-evidence-development-v0.4",
        "status": "development_only_seen_tasks",
        "tasks": len(cached),
        "candidate_policies": len(rows),
        "retrieval_policy": {"exact_quota": EXACT_QUOTA, "frontier_top_k": v02.TOP_K},
        "eligible_100_100": len(eligible),
        "selected": {k: v for k, v in best.items() if k != "task_rows"},
        "selected_task_rows": best["task_rows"],
        "top_eligible": [{k: v for k, v in row.items() if k != "task_rows"} for row in eligible[:10]],
        "claim_boundary": "All 14 tasks are already-observed development data. Hybrid cards combine generic coverage and contiguous behavior evidence; labels are post-hoc scoring only. Freeze before constructing any fresh unseen suite.",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
