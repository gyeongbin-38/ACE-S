#!/usr/bin/env python3
"""Development experiment: exact proof fast-path or bounded candidate frontier.

This deliberately removes forced deterministic top-1 selection for ambiguous
natural-language repository tasks. A task may terminate directly only when an
explicit prompt symbol has a unique production definition. Otherwise the
controller emits a small authenticated candidate frontier for a later semantic
judge.

Development only on the already-seen six-task source-evidence compatibility set.
Do not cite as unseen generalization evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization_v041 as v041  # noqa: E402

TASKSET = ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.2.json"
TOP_K = 8
LINES_PER_CARD = 4


def sha_line(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def direct_proof(by_file: dict[str, dict], prompt: str) -> tuple[str | None, list[str]]:
    proofs = v041.certified_definition_paths(by_file, prompt)
    paths = []
    symbols = []
    for symbol, files in proofs.items():
        if len(files) == 1:
            paths.append(files[0]); symbols.append(symbol)
    unique = sorted(set(paths))
    if len(unique) == 1:
        return unique[0], sorted(symbols)
    return None, []


def card_for(repo: Path, row: dict, terms: list[tuple[str, float, bool]]) -> dict:
    path = row["path"]
    src = repo / path
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    candidates = []
    for raw_lineno, _raw_text in row.get("hit_lines", []):
        try:
            lineno = int(raw_lineno)
        except (TypeError, ValueError):
            continue
        if not (1 <= lineno <= len(lines)):
            continue
        text = lines[lineno - 1]
        low = text.lower()
        score = 0.0
        for term, weight, exactish in terms:
            if term.lower() in low:
                score += weight * (2.0 if exactish else 1.0)
        candidates.append((score, lineno, text))
    if not candidates:
        for lineno, text in enumerate(lines, 1):
            low = text.lower()
            score = sum(weight for term, weight, _ in terms if term.lower() in low)
            if score:
                candidates.append((score, lineno, text))
    chosen = sorted({(s, n, t) for s, n, t in candidates}, key=lambda x: (-x[0], x[1], x[2]))[:LINES_PER_CARD]
    return {
        "path": path,
        "rank": row.get("rank"),
        "matched_terms": row.get("matched_terms", []),
        "records": [{"line": n, "text": t, "line_sha256": sha_line(t)} for _s, n, t in chosen],
        "provenance": f"git:{path}",
    }


def main() -> None:
    taskset = json.loads(TASKSET.read_text(encoding="utf-8"))
    rows = []
    false_confident = 0
    frontier_hits = 0
    anchor_hits = 0
    direct_count = 0
    total_raw_search = 0
    total_cards = 0

    for task in taskset["tasks"]:
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        terms = v03.smart_query_terms(task["prompt"])
        raw, _ms = v03.smart_grep_repo(repo, terms)
        by_file = base.parse_hits(raw, terms)
        ranked = v041.certified_rank(by_file, terms)
        for i, row in enumerate(ranked, 1):
            row["rank"] = i
        proof_path, proof_symbols = direct_proof(by_file, task["prompt"])
        expected = task["expected_file"]
        anchor = task["expected_anchor"].lower()

        if proof_path is not None:
            direct_count += 1
            direct_ok = proof_path == expected
            if not direct_ok:
                false_confident += 1
            cards = [card_for(repo, next(r for r in ranked if r["path"] == proof_path), terms)] if any(r["path"] == proof_path for r in ranked) else []
            mode = "DIRECT_CERTIFIED"
            frontier_ok = direct_ok
        else:
            cards = [card_for(repo, r, terms) for r in ranked[:TOP_K]]
            mode = "NEEDS_SEMANTIC_JUDGE"
            frontier_ok = any(c["path"] == expected for c in cards)

        if frontier_ok:
            frontier_hits += 1
        expected_cards = [c for c in cards if c["path"] == expected]
        anchor_visible = any(anchor in "\n".join(rec["text"] for rec in c["records"]).lower() for c in expected_cards)
        if anchor_visible:
            anchor_hits += 1

        raw_bytes = len(raw.encode("utf-8", errors="replace"))
        card_bytes = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        total_raw_search += raw_bytes
        total_cards += card_bytes
        rows.append({
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
        })

    result = {
        "experiment": "repo-proof-or-frontier-development-v0.1",
        "status": "development_only_seen_tasks",
        "tasks": len(rows),
        "direct_certified_tasks": direct_count,
        "semantic_judge_tasks": len(rows) - direct_count,
        "false_confident_direct_count": false_confident,
        "frontier_recall_pct": round(100 * frontier_hits / len(rows), 3),
        "expected_anchor_card_recall_pct": round(100 * anchor_hits / len(rows), 3),
        "raw_search_bytes_total": total_raw_search,
        "candidate_card_bytes_total": total_cards,
        "candidate_card_vs_raw_search_reduction_pct": round(100 * (1 - total_cards / total_raw_search), 3) if total_raw_search else 0.0,
        "rows": rows,
        "success_gate": {
            "false_confident_direct_eq_0": false_confident == 0,
            "frontier_recall_eq_100": frontier_hits == len(rows),
            "anchor_card_recall_eq_100": anchor_hits == len(rows),
        },
        "claim_boundary": "Seen-task controller development only. Candidate recall and authenticated card size are not semantic-judge accuracy or end-to-end LLM quality evidence."
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not all(result["success_gate"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
