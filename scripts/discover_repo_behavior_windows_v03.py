#!/usr/bin/env python3
"""Development v0.3: behavior-window evidence cards on the frozen v0.2 frontier.

Uses only already-observed tasks (6 original development + 8 v0.1 sealed tasks).
The v0.2 retrieval policy is held fixed at exact_quota=5 because it reached
100% frontier recall on these 14 tasks. This experiment changes only evidence
realization: instead of selecting isolated lines, it greedily packs a small
number of contiguous source windows that maximize marginal query-signal
coverage and preserve behavior-bearing structure.

Expected files/anchors are used only after card construction for scoring.
Development only. Any winning policy must be frozen before a fresh unseen suite.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
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
import run_repo_candidate_frontier_dev_v2 as old  # noqa: E402

EXACT_QUOTA = 5


@dataclass(frozen=True)
class WindowCfg:
    span: int
    max_windows: int
    overlap_merge_gap: int


WINDOW_CFGS = [
    WindowCfg(span, max_windows, 2)
    for span in (6, 8, 10, 12, 16, 20, 24)
    for max_windows in (1, 2, 3)
]


def decode_safe_grep(repo: Path, terms: list[tuple[str, float, bool]]) -> tuple[str, int]:
    if not terms:
        return "", 0
    cmd = ["git", "grep", "-n", "-I", "-i"]
    for term, _, _ in terms:
        cmd.extend(["-e", term])
    cmd.extend(["--", ":(exclude)*.lock"])
    cp = subprocess.run(cmd, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if cp.returncode not in {0, 1}:
        raise RuntimeError(cp.stderr.decode("utf-8", errors="replace")[-1000:])
    return cp.stdout.decode("utf-8", errors="replace"), len(cp.stdout)


def structural_score(text: str) -> float:
    s = text.strip()
    if not s:
        return 0.0
    score = 0.0
    if v02.is_definition_line(s):
        score += 2.0
    if v02.is_comment(s):
        score += 0.45
    if re.search(r"\b(if|else|elif|switch|match|for|while|try|catch|except|return|raise|throw|await)\b", s):
        score += 0.65
    if re.search(r"\b(split|read|write|set|append|remove|delete|contains|check|verify|resolve|build|load)\w*\s*\(", s, re.I):
        score += 0.55
    return score


def per_line_support(lines: list[str], terms: list[tuple[str, float, bool]]) -> list[dict[int, float]]:
    out: list[dict[int, float]] = []
    for text in lines:
        row: dict[int, float] = {}
        for i, (term, weight, exactish) in enumerate(terms):
            sig = v02.term_support(term, text)
            if sig:
                row[i] = weight * sig * (2.0 if exactish else 1.0)
        out.append(row)
    return out


def candidate_windows(lines: list[str], supports: list[dict[int, float]], span: int) -> list[tuple[int, int]]:
    n = len(lines)
    half = span // 2
    windows: set[tuple[int, int]] = set()
    for idx, support in enumerate(supports, start=1):
        if not support:
            continue
        start = max(1, idx - half)
        end = min(n, start + span - 1)
        start = max(1, end - span + 1)
        windows.add((start, end))
        # Also anchor a window with the hit near its beginning; useful for
        # comment -> implementation blocks and function docstrings.
        start2 = max(1, idx - 2)
        end2 = min(n, start2 + span - 1)
        windows.add((start2, end2))
    return sorted(windows)


def window_features(lines: list[str], supports: list[dict[int, float]], start: int, end: int):
    per_term: dict[int, float] = {}
    structural = 0.0
    nonblank = 0
    byte_cost = 0
    for n in range(start, end + 1):
        text = lines[n - 1]
        byte_cost += len((text + "\n").encode("utf-8", errors="replace"))
        if text.strip():
            nonblank += 1
        structural += structural_score(text)
        for term_id, value in supports[n - 1].items():
            per_term[term_id] = max(per_term.get(term_id, 0.0), value)
    density = nonblank / max(1, end - start + 1)
    return per_term, structural, density, byte_cost


def choose_windows(lines: list[str], terms: list[tuple[str, float, bool]], cfg: WindowCfg) -> list[tuple[int, int]]:
    supports = per_line_support(lines, terms)
    candidates = []
    for start, end in candidate_windows(lines, supports, cfg.span):
        per_term, structural, density, byte_cost = window_features(lines, supports, start, end)
        if not per_term:
            continue
        candidates.append({
            "start": start,
            "end": end,
            "per_term": per_term,
            "structural": structural,
            "density": density,
            "bytes": byte_cost,
        })

    selected: list[dict] = []
    covered: set[int] = set()
    remaining = candidates
    while remaining and len(selected) < cfg.max_windows:
        best = None
        best_key = None
        for w in remaining:
            new_gain = sum(v for i, v in w["per_term"].items() if i not in covered)
            repeat_gain = sum(v for i, v in w["per_term"].items() if i in covered)
            # Marginal coverage dominates. Structure and density break ties;
            # a tiny byte penalty prefers the smaller equally-informative unit.
            objective = (
                new_gain
                + 0.10 * repeat_gain
                + 0.30 * w["structural"]
                + 0.20 * w["density"]
                - 0.00008 * w["bytes"]
            )
            key = (objective, new_gain, w["structural"], -w["bytes"], -w["start"])
            if best_key is None or key > best_key:
                best_key = key
                best = w
        if best is None or best_key is None or best_key[0] <= 0:
            break
        selected.append(best)
        covered.update(best["per_term"])
        remaining = [
            w for w in remaining
            if not (w["start"] <= best["end"] + cfg.overlap_merge_gap and best["start"] <= w["end"] + cfg.overlap_merge_gap)
        ]

    # Merge nearby selected windows for a coherent worker-visible packet.
    intervals = sorted((w["start"], w["end"]) for w in selected)
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + cfg.overlap_merge_gap:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(a, b) for a, b in merged]


def behavior_card(repo: Path, row: dict, terms: list[tuple[str, float, bool]], cfg: WindowCfg) -> dict:
    path = row["path"]
    lines = (repo / path).read_text(encoding="utf-8", errors="replace").splitlines()
    windows = choose_windows(lines, terms, cfg)
    records = []
    for window_id, (start, end) in enumerate(windows, 1):
        for n in range(start, end + 1):
            records.append({"window": window_id, "line": n, "text": lines[n - 1]})
    return {"path": path, "windows": windows, "records": records}


def build_cache() -> list[dict]:
    cached = []
    for task in v02.load_tasks():
        repo = base.ensure_repo(task["repository"], task["commit_sha"])
        exact_terms = v03.smart_query_terms(task["prompt"])
        exact_raw, exact_bytes = decode_safe_grep(repo, exact_terms)
        exact_by = base.parse_hits(exact_raw, exact_terms)
        exact_ranked = v041.certified_rank(exact_by, exact_terms)
        for i, r in enumerate(exact_ranked, 1):
            r["rank"] = i
        proof_path, _symbols = old.direct_proof(exact_by, task["prompt"])

        recall_terms = v02.prefix_terms(exact_terms)
        recall_raw, recall_bytes = decode_safe_grep(repo, recall_terms)
        recall_by = base.parse_hits(recall_raw, recall_terms)
        recall_ranked = v03.smart_rank_files(recall_by, recall_terms)
        for i, r in enumerate(recall_ranked, 1):
            r["rank"] = i

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


def percentile(values: list[float], q: float) -> float:
    xs = sorted(values)
    if not xs:
        return 0.0
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def main() -> None:
    cached = build_cache()
    rows = []
    for cfg in WINDOW_CFGS:
        hits = anchors = false_direct = 0
        card_sizes = []
        task_rows = []
        for item in cached:
            t = item["task"]
            expected = t["expected_file"]
            anchor = t["expected_anchor"].lower()
            frontier_hit = any(r["path"] == expected for r in item["frontier"])
            if frontier_hit:
                hits += 1
            if item["proof_path"] is not None and item["proof_path"] != expected:
                false_direct += 1

            cards = [behavior_card(item["repo"], r, item["terms"], cfg) for r in item["frontier"]]
            expected_cards = [c for c in cards if c["path"] == expected]
            anchor_hit = any(anchor in "\n".join(x["text"] for x in c["records"]).lower() for c in expected_cards)
            if anchor_hit:
                anchors += 1
            cbytes = len(json.dumps(cards, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            card_sizes.append(cbytes)
            task_rows.append({
                "task_id": t["task_id"],
                "frontier_hit": frontier_hit,
                "anchor_hit": anchor_hit,
                "card_bytes": cbytes,
                "frontier": [r["path"] for r in item["frontier"]],
            })

        n = len(cached)
        rows.append({
            "cfg": asdict(cfg),
            "frontier_recall_pct": 100 * hits / n,
            "anchor_recall_pct": 100 * anchors / n,
            "false_direct": false_direct,
            "mean_card_bytes": sum(card_sizes) / n,
            "p95_card_bytes": percentile(card_sizes, 0.95),
            "max_card_bytes": max(card_sizes),
            "task_rows": task_rows,
        })

    eligible = [r for r in rows if r["false_direct"] == 0 and r["frontier_recall_pct"] == 100.0 and r["anchor_recall_pct"] == 100.0]
    eligible.sort(key=lambda r: (r["mean_card_bytes"], r["p95_card_bytes"], r["max_card_bytes"]))
    best = eligible[0] if eligible else max(rows, key=lambda r: (r["anchor_recall_pct"], -r["mean_card_bytes"]))
    out = {
        "experiment": "repo-behavior-window-cards-development-v0.3",
        "status": "development_only_seen_tasks",
        "tasks": len(cached),
        "candidate_policies": len(rows),
        "retrieval_policy": {"exact_quota": EXACT_QUOTA, "frontier_top_k": v02.TOP_K},
        "eligible_100_anchor": len(eligible),
        "selected": {k: v for k, v in best.items() if k != "task_rows"},
        "selected_task_rows": best["task_rows"],
        "top_eligible": [{k: v for k, v in r.items() if k != "task_rows"} for r in eligible[:8]],
        "claim_boundary": "Seen-task evidence-realization development only. Retrieval is fixed from v0.2. Expected anchors are post-hoc scoring labels and are never used to choose windows. Fresh sealed repositories are required before generalization claims.",
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
