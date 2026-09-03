#!/usr/bin/env python3
"""Development diagnostic: deterministic source-artifact hygiene.

For tasks explicitly asking for a production *source file*, measure whether
removing obvious non-source artifacts from the semantic frontier can reduce
candidate load without losing the expected implementation file.

This is intentionally separate from retrieval/card v0.4 so its effect is
attributable. It uses only already-observed 14 development tasks.
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

EXACT_QUOTA = 5
SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".go", ".java", ".kt", ".kts",
    ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".scala",
    ".sh", ".bash", ".zsh",
}


def is_source_artifact(path: str) -> bool:
    p = Path(path)
    name = p.name.lower()
    if name.endswith((".lock", "-lock.json", "lock.json", "lock.yaml", "lock.yml")):
        return False
    return p.suffix.lower() in SOURCE_SUFFIXES


def main():
    rows = []
    before_hits = after_hits = 0
    before_count = after_count = 0
    changed_tasks = 0

    for task in v02.load_tasks():
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

        if proof:
            before = [r for r in exact_ranked if r["path"] == proof][:1]
        else:
            before = v02.compose_frontier(exact_ranked, recall_ranked, EXACT_QUOTA)

        asks_source = "source file" in task["prompt"].lower()
        if asks_source:
            after = [r for r in before if is_source_artifact(r["path"])]
        else:
            after = list(before)

        expected = task["expected_file"]
        before_hit = any(r["path"] == expected for r in before)
        after_hit = any(r["path"] == expected for r in after)
        before_hits += int(before_hit); after_hits += int(after_hit)
        before_count += len(before); after_count += len(after)
        changed_tasks += int([r["path"] for r in before] != [r["path"] for r in after])
        rows.append({
            "task_id": task["task_id"],
            "before_count": len(before),
            "after_count": len(after),
            "removed": [r["path"] for r in before if r["path"] not in {x["path"] for x in after}],
            "before_hit": before_hit,
            "after_hit": after_hit,
        })

    n = len(rows)
    output = {
        "experiment": "production-source-artifact-hygiene-development-v0.1",
        "status": "development_only_seen_tasks",
        "tasks": n,
        "before_frontier_recall_pct": 100 * before_hits / n,
        "after_frontier_recall_pct": 100 * after_hits / n,
        "changed_tasks": changed_tasks,
        "mean_candidates_before": before_count / n,
        "mean_candidates_after": after_count / n,
        "candidate_reduction_pct": 100 * (1 - after_count / before_count) if before_count else 0.0,
        "rows": rows,
        "decision_rule": "Adopt only as a hard task-contract filter if recall is preserved exactly; this diagnostic does not alter v0.4 retrieval or evidence realization.",
        "claim_boundary": "Seen-task deterministic hygiene only; no semantic quality claim."
    }
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    main()
