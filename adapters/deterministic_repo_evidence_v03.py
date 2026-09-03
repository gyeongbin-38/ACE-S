#!/usr/bin/env python3
"""Development v0.3: proof-or-bounded-source-rerank evidence adapter.

If v0.4.1 has an exact unique symbol-definition certificate for the top result,
keep it unchanged. Otherwise, do not trust a hard one-shot lexical winner:
rerank only the top-k candidate frontier using BM25-like whole-source evidence
from the frozen checkout.

No repository/task IDs or expected paths are encoded. This is development on the
seen compatibility suite; freeze before any fresh OOD taskset.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import deterministic_repo_localization_v041 as v041  # noqa: E402
import deterministic_repo_localization_v03 as v03  # noqa: E402
import deterministic_repo_localization as base  # noqa: E402

ORIGINAL_CERTIFIED_RANK = v041.certified_rank
TOP_K = 8
GENERIC = {
    "locate", "production", "source", "file", "responsible", "return", "most",
    "relevant", "path", "behavior", "used", "when", "where", "that", "this",
    "with", "from", "into", "including", "containing", "contains", "involved",
    "handling", "may", "values", "data", "none", "different",
}


def camel_parts(token: str) -> list[str]:
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", token)
    return [p.lower() for p in parts if len(p) >= 3]


def query_atoms(prompt: str) -> list[tuple[str, float]]:
    merged: dict[str, float] = {}
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", prompt):
        low = raw.lower()
        if low in GENERIC:
            continue
        code_like = "_" in raw or "-" in raw or any(c.isupper() for c in raw[1:])
        weight = 4.0 if code_like else 1.0
        variants = {low}
        variants.update(camel_parts(raw))
        for part in re.split(r"[-_]", low):
            if len(part) >= 4:
                variants.add(part)
        # Prefix atom helps morphology such as originate/originating without a
        # language-specific stemmer. Only long natural-language atoms use it.
        if not code_like and len(low) >= 8:
            variants.add(low[:7])
        for atom in variants:
            if len(atom) >= 4:
                merged[atom] = max(merged.get(atom, 0.0), weight if atom == low else weight * 0.7)
    return sorted(merged.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))[:28]


def count_atom(text_low: str, atom: str) -> int:
    return text_low.count(atom)


def bounded_source_rerank(by_file, terms):
    rows = ORIGINAL_CERTIFIED_RANK(by_file, terms)
    if len(rows) <= 1:
        return rows
    # Proof-like unique definitions outrank heuristic reranking.
    if rows[0].get("certified_symbols"):
        return rows
    repo = v03.CURRENT_REPO
    if repo is None:
        return rows
    atoms = query_atoms(v03.CURRENT_PROMPT)
    if not atoms:
        return rows

    frontier = rows[:TOP_K]
    docs = []
    for row in frontier:
        path = repo / row["path"]
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            text = ""
        docs.append((row, text, max(1, len(text))))
    avg_len = sum(d[2] for d in docs) / len(docs)
    dfs = Counter()
    for atom, _w in atoms:
        for _row, text, _length in docs:
            if atom in text:
                dfs[atom] += 1

    k1, b = 1.2, 0.72
    for rank, (row, text, length) in enumerate(docs):
        score = 0.0
        path_low = row["path"].lower()
        for atom, qweight in atoms:
            tf = count_atom(text, atom)
            if tf <= 0:
                continue
            idf = math.log(1.0 + (len(docs) - dfs[atom] + 0.5) / (dfs[atom] + 0.5))
            denom = tf + k1 * (1 - b + b * length / avg_len)
            score += qweight * idf * (tf * (k1 + 1) / denom)
            if atom in path_low:
                score += 0.8 * qweight
        # Small prior only; it cannot overwhelm source evidence.
        score += 1.5 / (rank + 1)
        score += 0.08 * v03.path_intent_bonus(row["path"])
        row["source_rerank_score"] = score
        row["pre_source_rank"] = rank + 1

    frontier.sort(key=lambda r: (-r.get("source_rerank_score", 0.0), r.get("pre_source_rank", 999), r["path"]))
    return frontier + rows[TOP_K:]


base.rank_files = bounded_source_rerank

# Reuse v0.2's authenticity/certificate runtime after replacing the selector.
import deterministic_repo_evidence_v02 as runtime  # noqa: E402

if __name__ == "__main__":
    runtime.main()
