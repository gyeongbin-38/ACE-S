#!/usr/bin/env python3
"""Development v0.2: proof fast-path or coverage-aware candidate frontier.

Changes only evidence-card construction versus v0.1:
- candidate ranking/direct proof remain unchanged,
- cards are selected from the already-chosen candidate source file,
- seed lines maximize weighted query-signal coverage instead of global top-hit score,
- conservative lexical-prefix matching is used only inside a selected file so
  natural-language variants such as originate/originating can surface,
- each seed carries a one-line authentic source context window.

No expected file/anchor is used to construct cards. Those fields are read only
for post-execution development scoring.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization_v041 as v041  # noqa: E402

TASKSET = ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.2.json"
TOP_K = 8
SEED_LINES = 4
CONTEXT_RADIUS = 1
MAX_RECORDS = 12
PREFIX_LEN = 6


def sha_line(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def direct_proof(by_file: dict[str, dict], prompt: str) -> tuple[str | None, list[str]]:
    proofs = v041.certified_definition_paths(by_file, prompt)
    paths: list[str] = []
    symbols: list[str] = []
    for symbol, files in proofs.items():
        if len(files) == 1:
            paths.append(files[0])
            symbols.append(symbol)
    unique = sorted(set(paths))
    if len(unique) == 1:
        return unique[0], sorted(symbols)
    return None, []


def token_prefixes(text: str) -> set[str]:
    out = set()
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_]+", text.lower()):
        if len(tok) < 5:
            continue
        out.add(tok[: min(PREFIX_LEN, len(tok))])
    return out


def term_signal(term: str, line: str) -> float:
    """Return exact/prefix lexical support for one query term on one source line."""
    low = line.lower()
    if term.lower() in low:
        return 1.0
    q = token_prefixes(term)
    if not q:
        return 0.0
    l = token_prefixes(line)
    if q.issubset(l):
        return 0.55
    return 0.0


def candidate_seeds(lines: list[str], terms: list[tuple[str, float, bool]]) -> list[tuple[int, dict[int, float], float]]:
    rows: list[tuple[int, dict[int, float], float]] = []
    for lineno, text in enumerate(lines, 1):
        support: dict[int, float] = {}
        raw_score = 0.0
        for idx, (term, weight, exactish) in enumerate(terms):
            sig = term_signal(term, text)
            if not sig:
                continue
            value = weight * sig * (2.0 if exactish else 1.0)
            support[idx] = value
            raw_score += value
        if support:
            rows.append((lineno, support, raw_score))
    return rows


def choose_seeds(rows: list[tuple[int, dict[int, float], float]]) -> list[int]:
    selected: list[int] = []
    covered: set[int] = set()
    remaining = list(rows)
    while remaining and len(selected) < SEED_LINES:
        best = None
        best_key = None
        for lineno, support, raw_score in remaining:
            new_gain = sum(v for idx, v in support.items() if idx not in covered)
            repeated_gain = sum(v for idx, v in support.items() if idx in covered)
            # Coverage dominates; repeated relevance only breaks ties softly.
            objective = new_gain + 0.08 * repeated_gain + 0.02 * raw_score
            key = (objective, new_gain, raw_score, -lineno)
            if best_key is None or key > best_key:
                best_key = key
                best = (lineno, support)
        if best is None or best_key is None or best_key[0] <= 0:
            break
        lineno, support = best
        selected.append(lineno)
        covered.update(support)
        remaining = [r for r in remaining if r[0] != lineno]
    return selected


def card_for(repo: Path, row: dict, terms: list[tuple[str, float, bool]]) -> dict:
    path = row["path"]
    src = repo / path
    lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    seeds = choose_seeds(candidate_seeds(lines, terms))

    record_lines: set[int] = set()
    for seed in seeds:
        for lineno in range(max(1, seed - CONTEXT_RADIUS), min(len(lines), seed + CONTEXT_RADIUS) + 1):
            record_lines.add(lineno)
    ordered = sorted(record_lines)[:MAX_RECORDS]
    records = [
        {"line": n, "text": lines[n - 1], "line_sha256": sha_line(lines[n - 1]), "seed": n in seeds}
        for n in ordered
    ]
    return {
        "path": path,
        "rank": row.get("rank"),
        "matched_terms": row.get("matched_terms", []),
        "records": records,
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
        "experiment": "repo-proof-or-frontier-development-v0.2",
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
        "claim_boundary": "Seen-task controller development only. Coverage-aware cards are authenticated source evidence, not semantic-judge accuracy or end-to-end LLM quality evidence."
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not all(result["success_gate"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
