#!/usr/bin/env python3
"""Post-freeze unseen repository frontier evaluation v0.1.

Uses the frozen proof/frontier controller without modification on the sealed
8-repository taskset. Produces two outputs:
  1) internal scored metrics (labels visible only to scorer),
  2) blind semantic-judge packets with labels/ranks removed and candidate order
     deterministically shuffled.

Do not modify the frozen controller after unseen execution begins. Any policy
change requires a new frozen controller and new unseen taskset.
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "adapters"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization_v041 as v041  # noqa: E402
import run_repo_candidate_frontier_dev_v2 as frozen  # noqa: E402

TASKSET = ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json"
FREEZE = ROOT / "benchmarks/frozen-repo-proof-frontier-v0.1.json"
OUT_DIR = ROOT / "artifacts/repo-frontier-unseen-v0.1"
FROZEN_CONTROLLER_BLOB_SHA = "93cee5b819d5485d367c79287a92bf6945ff4359"
SHUFFLE_SEED = 20260903


def assert_frozen_controller() -> None:
    path = ROOT / "scripts/run_repo_candidate_frontier_dev_v2.py"
    got = subprocess.run(
        ["git", "hash-object", str(path)], check=True, text=True, capture_output=True
    ).stdout.strip()
    if got != FROZEN_CONTROLLER_BLOB_SHA:
        raise SystemExit(
            f"frozen controller mismatch: expected {FROZEN_CONTROLLER_BLOB_SHA}, got {got}"
        )


def stable_rng(task_id: str) -> random.Random:
    digest = hashlib.sha256(f"{SHUFFLE_SEED}:{task_id}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def blind_packet(task: dict, cards: list[dict]) -> dict:
    cards = list(cards)
    stable_rng(task["task_id"]).shuffle(cards)
    candidates = []
    eid = 1
    for idx, card in enumerate(cards, 1):
        evidence = []
        for rec in card["records"]:
            evidence.append(
                {
                    "evidence_id": f"E{eid}",
                    "line": rec["line"],
                    "text": rec["text"],
                    "line_sha256": rec["line_sha256"],
                }
            )
            eid += 1
        candidates.append(
            {
                "candidate_id": f"C{idx}",
                "path": card["path"],
                "provenance": card["provenance"],
                "evidence": evidence,
            }
        )
    return {
        "task_id": task["task_id"],
        "task": task["prompt"],
        "candidates": candidates,
        "output_contract": {
            "decision": "SELECT | ABSTAIN",
            "candidate_id": "provided candidate id or null",
            "confidence": "HIGH | MEDIUM | LOW",
            "evidence_refs": "list of provided evidence ids",
            "reason": "brief evidence-grounded explanation",
        },
    }


def main() -> None:
    assert_frozen_controller()
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    taskset = json.loads(TASKSET.read_text(encoding="utf-8"))
    if freeze["status"] != "frozen_before_unseen_repo_execution":
        raise SystemExit("unexpected freeze status")
    if taskset["status"] != "frozen_before_controller_execution":
        raise SystemExit("unexpected taskset status")

    scored_rows = []
    packets = []
    total_raw = 0
    total_cards = 0
    direct_count = 0
    false_confident = 0
    frontier_hits = 0
    anchor_hits = 0

    for task in taskset["tasks"]:
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        terms = v03.smart_query_terms(task["prompt"])
        raw, _ms = v03.smart_grep_repo(repo, terms)
        by_file = base.parse_hits(raw, terms)
        ranked = v041.certified_rank(by_file, terms)
        for i, row in enumerate(ranked, 1):
            row["rank"] = i

        proof_path, proof_symbols = frozen.direct_proof(by_file, task["prompt"])
        expected = task["expected_file"]
        anchor = task["expected_anchor"].lower()

        if proof_path is not None:
            direct_count += 1
            direct_ok = proof_path == expected
            if not direct_ok:
                false_confident += 1
            cards = [
                frozen.card_for(repo, next(r for r in ranked if r["path"] == proof_path), terms)
            ] if any(r["path"] == proof_path for r in ranked) else []
            mode = "DIRECT_CERTIFIED"
            frontier_ok = direct_ok
        else:
            cards = [frozen.card_for(repo, r, terms) for r in ranked[: frozen.TOP_K]]
            mode = "NEEDS_SEMANTIC_JUDGE"
            frontier_ok = any(c["path"] == expected for c in cards)

        if frontier_ok:
            frontier_hits += 1
        expected_cards = [c for c in cards if c["path"] == expected]
        anchor_visible = any(
            anchor in "\n".join(rec["text"] for rec in c["records"]).lower()
            for c in expected_cards
        )
        if anchor_visible:
            anchor_hits += 1

        raw_bytes = len(raw.encode("utf-8", errors="replace"))
        card_bytes = len(
            json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        total_raw += raw_bytes
        total_cards += card_bytes

        scored_rows.append(
            {
                "task_id": task["task_id"],
                "mode": mode,
                "proof_symbols": proof_symbols,
                "direct_path": proof_path,
                "expected_file": expected,
                "frontier_paths": [c["path"] for c in cards],
                "frontier_hit": frontier_ok,
                "expected_anchor_visible": anchor_visible,
                "raw_search_bytes": raw_bytes,
                "candidate_card_bytes": card_bytes,
            }
        )
        if mode == "NEEDS_SEMANTIC_JUDGE":
            packets.append(blind_packet(task, cards))

    n = len(scored_rows)
    result = {
        "experiment": "repo-proof-or-frontier-sealed-unseen-v0.1",
        "status": "post_freeze_unseen_controller_execution",
        "controller_freeze": freeze["artifact"],
        "controller_blob_sha": FROZEN_CONTROLLER_BLOB_SHA,
        "taskset_commit": "ef8676375b3edc726db6c088b9dff6d4bfe09944",
        "tasks": n,
        "direct_certified_tasks": direct_count,
        "semantic_judge_tasks": len(packets),
        "false_confident_direct_count": false_confident,
        "frontier_recall_pct": round(100 * frontier_hits / n, 3),
        "expected_anchor_card_recall_pct": round(100 * anchor_hits / n, 3),
        "raw_search_bytes_total": total_raw,
        "candidate_card_bytes_total": total_cards,
        "candidate_card_vs_raw_search_reduction_pct": round(100 * (1 - total_cards / total_raw), 3) if total_raw else 0.0,
        "rows": scored_rows,
        "claim_boundary": "Post-freeze unseen repository localization/frontier mechanics. Semantic judge accuracy is not included until blind external judge outputs are scored."
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "internal-score.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "blind-judge-packets.json").write_text(
        json.dumps({"schema_version": "0.1", "packets": packets}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"BLIND_PACKETS={OUT_DIR / 'blind-judge-packets.json'}")


if __name__ == "__main__":
    main()
