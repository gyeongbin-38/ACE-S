#!/usr/bin/env python3
"""Fast diagnostic for the two v0.2 evidence-realization misses.

Runs the exact v0.3 behavior-window candidates on Click and Axios only. This is
seen-task development diagnostics; it does not change policy or support a
Generalization claim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base
import deterministic_repo_localization_v03 as v03
import deterministic_repo_localization_v041 as v041
import discover_repo_frontier_v02 as v02
import discover_repo_behavior_windows_v03 as v03w
import run_repo_candidate_frontier_dev_v2 as old

TASK_IDS = {"click-envvar-splitting-001", "axios-xsrf-origin-001"}


def tasks():
    data = json.loads((ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json").read_text(encoding="utf-8"))
    return [t for t in data["tasks"] if t["task_id"] in TASK_IDS]


def build(task):
    repo = base.ensure_repo(task["repository"], task["commit_sha"])
    exact_terms = v03.smart_query_terms(task["prompt"])
    exact_raw, _ = v03w.decode_safe_grep(repo, exact_terms)
    exact_by = base.parse_hits(exact_raw, exact_terms)
    exact_ranked = v041.certified_rank(exact_by, exact_terms)
    for i, r in enumerate(exact_ranked, 1): r["rank"] = i
    proof, _ = old.direct_proof(exact_by, task["prompt"])
    recall_terms = v02.prefix_terms(exact_terms)
    recall_raw, _ = v03w.decode_safe_grep(repo, recall_terms)
    recall_by = base.parse_hits(recall_raw, recall_terms)
    recall_ranked = v03.smart_rank_files(recall_by, recall_terms)
    for i, r in enumerate(recall_ranked, 1): r["rank"] = i
    frontier = ([r for r in exact_ranked if r["path"] == proof][:1] if proof else v02.compose_frontier(exact_ranked, recall_ranked, v03w.EXACT_QUOTA))
    return repo, exact_terms + recall_terms, frontier


def main():
    built = [(t, *build(t)) for t in tasks()]
    rows = []
    for cfg in v03w.WINDOW_CFGS:
        task_rows = []
        hits = 0
        total_bytes = 0
        for t, repo, terms, frontier in built:
            cards = [v03w.behavior_card(repo, r, terms, cfg) for r in frontier]
            expected_cards = [c for c in cards if c["path"] == t["expected_file"]]
            anchor = t["expected_anchor"].lower()
            ok = any(anchor in "\n".join(x["text"] for x in c["records"]).lower() for c in expected_cards)
            hits += int(ok)
            cbytes = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode())
            total_bytes += cbytes
            task_rows.append({"task_id": t["task_id"], "anchor_hit": ok, "card_bytes": cbytes})
        rows.append({"cfg": v03w.asdict(cfg), "anchor_hits": hits, "mean_card_bytes": total_bytes / len(built), "tasks": task_rows})
    passing = [r for r in rows if r["anchor_hits"] == len(built)]
    passing.sort(key=lambda r: r["mean_card_bytes"])
    print(json.dumps({"experiment":"behavior-window-fast-diagnostic-v0.3","passing_configs":len(passing),"best":passing[0] if passing else None,"top":passing[:8]}, indent=2))

if __name__ == "__main__":
    main()
