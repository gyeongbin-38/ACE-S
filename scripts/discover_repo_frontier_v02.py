#!/usr/bin/env python3
"""Development search for repository frontier v0.2.

Uses only already-observed tasks: the six-task source-evidence development set
plus the eight-task v0.1 sealed set, which becomes development data after its
first sealed execution.

Hypothesis:
- keep the current exact lexical channel as the precision channel,
- add a conservative prefix-recall channel only for candidate nomination,
- never let recall-channel evidence create a direct proof,
- preserve small behavior-bearing source units instead of isolated top lines.

This is development only. A winning policy must be frozen before a completely
new repository/taskset is constructed.
"""
from __future__ import annotations

import json
import math
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))
sys.path.insert(0, str(ROOT / "scripts"))

import deterministic_repo_localization as base  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization_v041 as v041  # noqa: E402
import run_repo_candidate_frontier_dev_v2 as old  # noqa: E402

DEVSETS = [
    ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.2.json",
    ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json",
]
TOP_K = 8
PREFIX_LEN = 6


@dataclass(frozen=True)
class CardCfg:
    seed_lines: int
    radius: int
    def_lookback: int
    comment_lookback: int
    max_records: int


CARD_CFGS = [
    CardCfg(4, 1, 12, 3, 16),
    CardCfg(4, 2, 16, 4, 24),
    CardCfg(6, 1, 16, 4, 24),
    CardCfg(6, 2, 20, 5, 32),
    CardCfg(8, 1, 20, 5, 32),
]
EXACT_QUOTAS = [2, 3, 4, 5, 6, 7]


def load_tasks() -> list[dict]:
    out = []
    for path in DEVSETS:
        out.extend(json.loads(path.read_text(encoding="utf-8"))["tasks"])
    return out


def prefix_terms(terms: list[tuple[str, float, bool]]) -> list[tuple[str, float, bool]]:
    merged: dict[str, float] = {}
    for term, weight, _exactish in terms:
        # Prefix recall is intentionally conservative and candidate-only.
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9_]+", term.lower()):
            if len(tok) < 7:
                continue
            pref = tok[:PREFIX_LEN]
            merged[pref] = max(merged.get(pref, 0.0), weight * 0.42)
    return sorted([(t, w, False) for t, w in merged.items()], key=lambda x: (-x[1], x[0]))[:16]


def grep(repo: Path, terms: list[tuple[str, float, bool]]) -> tuple[str, int]:
    if not terms:
        return "", 0
    cmd = ["git", "grep", "-n", "-I", "-i"]
    for term, _, _ in terms:
        cmd.extend(["-e", term])
    cmd.extend(["--", ":(exclude)*.lock"])
    cp = subprocess.run(cmd, cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode not in {0, 1}:
        raise RuntimeError(cp.stderr[-1000:])
    raw = cp.stdout
    return raw, len(raw.encode("utf-8", errors="replace"))


def merge_row(path: str, exact_row: dict | None, recall_row: dict | None) -> dict:
    lines = []
    seen = set()
    matched = set()
    rank = None
    for row in (exact_row, recall_row):
        if not row:
            continue
        matched.update(row.get("matched_terms", []))
        rank = row.get("rank", rank)
        for n, text in row.get("hit_lines", []):
            key = (str(n), text)
            if key not in seen:
                seen.add(key); lines.append((n, text))
    return {
        "path": path,
        "rank": rank,
        "matched_terms": sorted(matched),
        "hit_lines": lines,
    }


def compose_frontier(exact_ranked: list[dict], recall_ranked: list[dict], exact_quota: int) -> list[dict]:
    exact_map = {r["path"]: r for r in exact_ranked}
    recall_map = {r["path"]: r for r in recall_ranked}
    chosen: list[str] = []
    for row in exact_ranked[:exact_quota]:
        if row["path"] not in chosen:
            chosen.append(row["path"])
    for row in recall_ranked:
        if len(chosen) >= TOP_K:
            break
        if row["path"] not in chosen:
            chosen.append(row["path"])
    for row in exact_ranked:
        if len(chosen) >= TOP_K:
            break
        if row["path"] not in chosen:
            chosen.append(row["path"])
    return [merge_row(p, exact_map.get(p), recall_map.get(p)) for p in chosen]


def is_definition_line(text: str) -> bool:
    low = text.strip()
    patterns = [
        r"^(?:async\s+)?def\s+\w+",
        r"^func\s+(?:\([^)]*\)\s*)?\w+",
        r"^(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+\w+",
        r"^(?:export\s+)?(?:async\s+)?function\s+\w+",
        r"^(?:export\s+)?(?:const|let|var)\s+\w+\s*=",
        r"^(?:public|private|protected|static|final|synchronized|abstract|default|override|@Override|\s)+[^;{}]*\w+\s*\([^;]*\)\s*(?:\{|throws|$)",
        r"^(?:class|interface|struct|enum|type)\s+\w+",
    ]
    return any(re.search(p, low) for p in patterns)


def is_comment(text: str) -> bool:
    s = text.strip()
    return s.startswith(("#", "//", "/*", "*", "///", '"""', "'''"))


def term_support(term: str, line: str) -> float:
    low = line.lower()
    if term.lower() in low:
        return 1.0
    q = old.token_prefixes(term)
    if q and q.issubset(old.token_prefixes(line)):
        return 0.55
    return 0.0


def choose_seed_lines(lines: list[str], terms: list[tuple[str, float, bool]], limit: int) -> list[int]:
    rows = []
    for lineno, text in enumerate(lines, 1):
        support = {}
        raw = 0.0
        for i, (term, weight, exactish) in enumerate(terms):
            sig = term_support(term, text)
            if sig:
                val = weight * sig * (2.0 if exactish else 1.0)
                support[i] = val; raw += val
        if support:
            rows.append((lineno, support, raw))
    selected, covered = [], set()
    remaining = list(rows)
    while remaining and len(selected) < limit:
        best = None; best_key = None
        for lineno, support, raw in remaining:
            new = sum(v for i, v in support.items() if i not in covered)
            repeat = sum(v for i, v in support.items() if i in covered)
            structural = 0.25 if is_definition_line(lines[lineno - 1]) else 0.0
            key = (new + 0.08 * repeat + 0.02 * raw + structural, new, raw, -lineno)
            if best_key is None or key > best_key:
                best_key = key; best = (lineno, support)
        if best is None or best_key[0] <= 0:
            break
        lineno, support = best
        selected.append(lineno); covered.update(support)
        remaining = [r for r in remaining if r[0] != lineno]
    return selected


def semantic_card(repo: Path, row: dict, terms: list[tuple[str, float, bool]], cfg: CardCfg) -> dict:
    path = row["path"]
    lines = (repo / path).read_text(encoding="utf-8", errors="replace").splitlines()
    seeds = choose_seed_lines(lines, terms, cfg.seed_lines)
    wanted: set[int] = set()
    for seed in seeds:
        # Local evidence window.
        for n in range(max(1, seed - cfg.radius), min(len(lines), seed + cfg.radius) + 1):
            wanted.add(n)

        # Pull in nearest behavior-bearing definition/header.
        start = max(1, seed - cfg.def_lookback)
        defline = None
        for n in range(seed, start - 1, -1):
            if is_definition_line(lines[n - 1]):
                defline = n; break
        if defline is not None:
            wanted.add(defline)
            # Preserve nearby leading comments/docstrings as provenance semantics.
            for n in range(max(1, defline - cfg.comment_lookback), defline):
                if is_comment(lines[n - 1]) or not lines[n - 1].strip():
                    wanted.add(n)

        # If seed is a comment, include the next nearby definition/body line.
        if is_comment(lines[seed - 1]):
            for n in range(seed + 1, min(len(lines), seed + 6) + 1):
                wanted.add(n)
                if is_definition_line(lines[n - 1]):
                    break

    # Rank records: seed first, then definition/comment context, then source order.
    def priority(n: int):
        text = lines[n - 1]
        return (0 if n in seeds else 1 if is_definition_line(text) else 2 if is_comment(text) else 3, n)

    kept = sorted(sorted(wanted, key=priority)[: cfg.max_records])
    return {
        "path": path,
        "records": [{"line": n, "text": lines[n - 1]} for n in kept],
    }


def main() -> None:
    tasks = load_tasks()
    cached = []
    for task in tasks:
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        exact_terms = v03.smart_query_terms(task["prompt"])
        exact_raw, exact_bytes = grep(repo, exact_terms)
        exact_by = base.parse_hits(exact_raw, exact_terms)
        exact_ranked = v041.certified_rank(exact_by, exact_terms)
        for i, r in enumerate(exact_ranked, 1): r["rank"] = i
        proof_path, _symbols = old.direct_proof(exact_by, task["prompt"])

        recall_terms = prefix_terms(exact_terms)
        recall_raw, recall_bytes = grep(repo, recall_terms)
        recall_by = base.parse_hits(recall_raw, recall_terms)
        recall_ranked = v03.smart_rank_files(recall_by, recall_terms)
        for i, r in enumerate(recall_ranked, 1): r["rank"] = i

        cached.append({
            "task": task, "repo": repo, "exact_terms": exact_terms, "recall_terms": recall_terms,
            "exact_ranked": exact_ranked, "recall_ranked": recall_ranked,
            "proof_path": proof_path, "exact_bytes": exact_bytes, "recall_bytes": recall_bytes,
        })

    rows = []
    for quota in EXACT_QUOTAS:
        for cfg in CARD_CFGS:
            hits = anchors = false_direct = direct_count = 0
            total_cards = total_search = 0
            task_rows = []
            for item in cached:
                t = item["task"]; expected = t["expected_file"]; anchor = t["expected_anchor"].lower()
                if item["proof_path"] is not None:
                    direct_count += 1
                    ok = item["proof_path"] == expected
                    if not ok: false_direct += 1
                    frontier = [r for r in item["exact_ranked"] if r["path"] == item["proof_path"]][:1]
                else:
                    frontier = compose_frontier(item["exact_ranked"], item["recall_ranked"], quota)
                    ok = any(r["path"] == expected for r in frontier)
                if ok: hits += 1

                terms = item["exact_terms"] + item["recall_terms"]
                cards = [semantic_card(item["repo"], r, terms, cfg) for r in frontier]
                expected_cards = [c for c in cards if c["path"] == expected]
                anchor_ok = any(anchor in "\n".join(x["text"] for x in c["records"]).lower() for c in expected_cards)
                if anchor_ok: anchors += 1
                cbytes = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode())
                sbytes = item["exact_bytes"] + item["recall_bytes"]
                total_cards += cbytes; total_search += sbytes
                task_rows.append({"task_id": t["task_id"], "frontier_hit": ok, "anchor_hit": anchor_ok, "frontier": [r["path"] for r in frontier], "card_bytes": cbytes})

            n = len(cached)
            rows.append({
                "exact_quota": quota,
                "card_cfg": asdict(cfg),
                "frontier_recall_pct": 100 * hits / n,
                "anchor_recall_pct": 100 * anchors / n,
                "false_direct": false_direct,
                "direct_count": direct_count,
                "mean_card_bytes": total_cards / n,
                "mean_search_bytes": total_search / n,
                "task_rows": task_rows,
            })

    # Quality gates first, then minimize card bytes; search bytes are constant across policies.
    eligible = [r for r in rows if r["false_direct"] == 0 and r["frontier_recall_pct"] == 100.0 and r["anchor_recall_pct"] == 100.0]
    eligible.sort(key=lambda r: (r["mean_card_bytes"], -r["exact_quota"]))
    best = eligible[0] if eligible else max(rows, key=lambda r: (r["frontier_recall_pct"], r["anchor_recall_pct"], -r["mean_card_bytes"]))
    out = {
        "experiment": "dual-channel-repo-frontier-development-v0.2",
        "status": "development_only_seen_tasks",
        "tasks": len(cached),
        "candidate_policies": len(rows),
        "eligible_100_100": len(eligible),
        "selected": {k:v for k,v in best.items() if k != "task_rows"},
        "selected_task_rows": best["task_rows"],
        "top_eligible": [{k:v for k,v in r.items() if k != "task_rows"} for r in eligible[:8]],
        "claim_boundary": "Uses already-observed tasks only. Prefix recall is candidate-only and cannot create direct proof. A selected policy must be frozen before any new unseen taskset is built.",
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
