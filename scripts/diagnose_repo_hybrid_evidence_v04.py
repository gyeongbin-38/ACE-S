#!/usr/bin/env python3
"""Fast v0.4 diagnostic on complementary evidence failure modes.

Seen-task diagnostic only: Kubernetes (coverage-sensitive) plus Click/Axios
(behavior-window-sensitive). Uses exactly the v0.4 policy family.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import discover_repo_hybrid_evidence_v04 as h

TASK_IDS = {
    "k8s-current-context-evidence-001",
    "click-envvar-splitting-001",
    "axios-xsrf-origin-001",
}


def main():
    cached = [item for item in h.build_cache() if item["task"]["task_id"] in TASK_IDS]
    rows = []
    for cfg in h.CONFIGS:
        hits = 0
        sizes = []
        per_task = []
        for item in cached:
            task = item["task"]
            cards = [h.hybrid_card(item["repo"], row, item["terms"], cfg) for row in item["frontier"]]
            expected_cards = [c for c in cards if c["path"] == task["expected_file"]]
            anchor = task["expected_anchor"].lower()
            ok = any(anchor in "\n".join(r["text"] for r in c["records"]).lower() for c in expected_cards)
            hits += int(ok)
            size = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            sizes.append(size)
            per_task.append({"task_id": task["task_id"], "anchor_hit": ok, "card_bytes": size})
        rows.append({"cfg": h.asdict(cfg), "hits": hits, "mean_card_bytes": sum(sizes)/len(sizes), "tasks": per_task})
    passing = [r for r in rows if r["hits"] == len(cached)]
    passing.sort(key=lambda r: r["mean_card_bytes"])
    print(json.dumps({
        "experiment": "repo-hybrid-evidence-fast-diagnostic-v0.4",
        "tasks": len(cached),
        "candidate_policies": len(rows),
        "passing_configs": len(passing),
        "best": passing[0] if passing else None,
        "top": passing[:10],
        "claim_boundary": "Seen-task diagnostic only; the full 14-task run controls freeze eligibility."
    }, indent=2))

if __name__ == "__main__":
    main()
