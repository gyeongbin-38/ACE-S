#!/usr/bin/env python3
"""Symbol-aware development adapter for real-repository localization.

General changes versus v0.2:
- definition sites outrank imports/usages,
- hyphenated task terms also search spaced/camel variants,
- high-scoring test files can nominate a same-module production sibling,
- path intent (utility/loader/adapter/factory) is a weak tie-breaker.

No task IDs, expected paths, repository names, or benchmark ground truth are
encoded here. v0.1 runtime pilot is development evidence only after observation.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import deterministic_repo_localization_v02 as robust
import deterministic_repo_localization as base

CURRENT_PROMPT = ""
CURRENT_REPO: Path | None = None

ORIGINAL_GREP = base.grep_repo
ORIGINAL_IS_PROD = base.is_prod_path


def smart_query_terms(prompt: str):
    global CURRENT_PROMPT
    CURRENT_PROMPT = prompt
    rows = list(base.query_terms(prompt))
    merged = {t.lower(): [w, e] for t, w, e in rows}
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", prompt):
        if "-" in tok or "_" in tok:
            parts = [p for p in re.split(r"[-_]", tok) if p]
            if len(parts) >= 2:
                spaced = " ".join(parts).lower()
                merged[spaced] = [max(merged.get(spaced, [0, False])[0], 8.0), True]
                pascal = "".join(p[:1].upper() + p[1:] for p in parts).lower()
                merged[pascal] = [max(merged.get(pascal, [0, False])[0], 7.0), True]
    out = [(t, w, e) for t, (w, e) in merged.items()]
    out.sort(key=lambda x: (-x[1], -len(x[0]), x[0]))
    return out[:22]


def allow_search_path(path: str) -> bool:
    # Search tests as structural evidence, but never return them as the final target.
    p = Path(path)
    if p.suffix.lower() not in base.CODE_EXTS:
        return False
    lowered = {x.lower() for x in p.parts}
    hard_exclude = {"docs", "doc", "examples", "example", "vendor", "third_party", "node_modules", "benchmarks", "benchmark", "generated", "dist", "build", "changelog", ".github"}
    return not bool(lowered & hard_exclude)


def smart_grep_repo(repo: Path, terms):
    global CURRENT_REPO
    CURRENT_REPO = repo
    return ORIGINAL_GREP(repo, terms)


def is_test_path(path: str) -> bool:
    p = Path(path)
    parts = {x.lower() for x in p.parts}
    name = p.name.lower()
    return bool(parts & {"test", "tests", "testing", "fixtures", "fixture"}) or name.startswith("test_") or name.endswith("_test.go") or name.endswith("test.java") or name.endswith("tests.py") or name.endswith(".test.ts") or name.endswith(".spec.ts")


def sibling_candidates(path: str) -> list[str]:
    p = Path(path)
    n = p.name
    names = []
    if n.endswith("_test.go"):
        names.append(n[:-8] + ".go")
    if n.startswith("test_") and n.endswith(".py"):
        names.append(n[5:])
    if n.endswith("_test.py"):
        names.append(n[:-8] + ".py")
    if n.endswith("Test.java"):
        names.append(n[:-9] + ".java")
    if n.endswith("Tests.java"):
        names.append(n[:-10] + ".java")
    if n.endswith(".test.ts"):
        names.append(n[:-8] + ".ts")
    if n.endswith(".spec.ts"):
        names.append(n[:-8] + ".ts")
    return [str(p.with_name(x)).replace("\\", "/") for x in names]


def path_intent_bonus(path: str) -> float:
    low_prompt = CURRENT_PROMPT.lower()
    low_path = path.lower()
    bonus = 0.0
    hints = [
        (("utility", "util"), ("util", "utils"), 18.0),
        (("loader", "loading", "written", "configuration"), ("loader", "load"), 12.0),
        (("adapter", "deserialization", "deserializer"), ("adapter", "factory", "bind"), 11.0),
        (("map", "deserialization"), ("map",), 8.0),
        (("authentication", "credentials"), ("auth", "util"), 7.0),
        (("tree", "path"), ("tree",), 6.0),
    ]
    for prompt_terms, path_terms, weight in hints:
        if any(x in low_prompt for x in prompt_terms) and any(x in low_path for x in path_terms):
            bonus += weight
    return bonus


def definition_bonus(row: dict, meta: dict[str, tuple[float, bool]]) -> float:
    score = 0.0
    for _, text in row["hit_lines"]:
        low = text.lower().strip()
        matched_exact = [t for t in row["matched_terms"] if meta.get(t, (0, False))[1] and t in low]
        if not matched_exact:
            continue
        # Language-neutral definition-ish signals.
        if re.search(r"\b(def|class|func|function|interface|type|struct|enum)\b", low):
            score += 55.0 + 8.0 * len(matched_exact)
        elif re.search(r"\b(export\s+)?(const|let|var|public|private|protected|static)\b", low) and ("=" in low or "(" in low):
            score += 32.0 + 5.0 * len(matched_exact)
        if re.search(r"\b(import|from|require)\b", low):
            score -= 18.0
    return score


def smart_rank_files(by_file: dict[str, dict], terms):
    if not by_file:
        return []
    n = len(by_file)
    df = Counter()
    for rec in by_file.values():
        for term in rec["tf"]:
            df[term] += 1
    meta = {t.lower(): (w, exactish) for t, w, exactish in terms}
    rows = []
    row_by_path = {}
    for path, rec in by_file.items():
        score = 0.0
        exact_hits = 0
        matched = []
        path_low = path.lower()
        for term, tf in rec["tf"].items():
            w, exactish = meta[term]
            idf = math.log((n + 1.0) / (df[term] + 1.0)) + 1.0
            contribution = w * idf * (1.0 + math.log1p(tf))
            if exactish:
                contribution *= 2.4
                exact_hits += 1
            if term in path_low:
                contribution *= 1.3
            score += contribution
            matched.append(term)
        row = {
            "path": path,
            "score": score,
            "exact_hits": exact_hits,
            "matched_terms": sorted(matched),
            "hit_bytes": rec["bytes"],
            "hit_lines": rec["lines"],
        }
        row["score"] += definition_bonus(row, meta) + path_intent_bonus(path)
        row["score"] -= 0.0006 * rec["bytes"]
        if is_test_path(path):
            row["score"] -= 28.0
        rows.append(row)
        row_by_path[path] = row

    # Structural-sibling bridge from high-value tests. This does not use benchmark labels.
    if CURRENT_REPO is not None:
        for row in list(rows):
            if not is_test_path(row["path"]):
                continue
            for sibling in sibling_candidates(row["path"]):
                if not (CURRENT_REPO / sibling).is_file():
                    continue
                existing = row_by_path.get(sibling)
                bridge_score = row["score"] + 34.0
                if existing is None:
                    existing = {
                        "path": sibling,
                        "score": bridge_score,
                        "exact_hits": row["exact_hits"],
                        "matched_terms": row["matched_terms"],
                        "hit_bytes": 0,
                        "hit_lines": [],
                    }
                    rows.append(existing)
                    row_by_path[sibling] = existing
                else:
                    existing["score"] = max(existing["score"], bridge_score)

    prod = [r for r in rows if not is_test_path(r["path"]) and ORIGINAL_IS_PROD(r["path"])]
    prod.sort(key=lambda r: (-r["exact_hits"], -r["score"], r["hit_bytes"], r["path"]))
    return prod


base.query_terms = smart_query_terms
base.is_prod_path = allow_search_path
base.grep_repo = smart_grep_repo
base.rank_files = smart_rank_files

if __name__ == "__main__":
    base.main()
