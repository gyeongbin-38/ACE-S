#!/usr/bin/env python3
"""Development adapter with a proof-like exact-symbol gate.

Policy order:
1. If the prompt names a code-like symbol and exactly one production file in
   the retrieved evidence defines that exact symbol, rank that file first.
2. Otherwise use the v0.3 semantic/definition/structural scorer with weak
   code-prefix variants for long natural-language terms.

The exact-symbol rule abstains when definition uniqueness is not established.
"""
from __future__ import annotations

import re

import deterministic_repo_localization_v03 as prev
import deterministic_repo_localization as base

ORIGINAL_SMART_QUERY = prev.smart_query_terms
ORIGINAL_SMART_RANK = prev.smart_rank_files

GENERIC_PROSE = {
    "Locate", "Return", "production", "source", "file", "behavior", "including",
    "configuration", "responsible", "implementing", "containing", "relevant",
}


def prompt_symbols(prompt: str) -> list[str]:
    out = []
    for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", prompt):
        if tok in GENERIC_PROSE:
            continue
        code_like = "_" in tok or any(c.isupper() for c in tok[1:])
        if code_like:
            out.append(tok)
    return list(dict.fromkeys(out))


def expanded_query(prompt: str):
    rows = list(ORIGINAL_SMART_QUERY(prompt))
    merged = {t.lower(): [w, e] for t, w, e in rows}
    # Weak code-prefix variants bridge prose morphology to identifiers/comments.
    # Prefixes are intentionally lower-weight than exact/code-like terms.
    for word in re.findall(r"\b[A-Za-z]{8,}\b", prompt):
        low = word.lower()
        if low in base.STOPWORDS:
            continue
        prefix_len = 6 if len(low) >= 10 else 5
        prefix = low[:prefix_len]
        if prefix not in merged:
            merged[prefix] = [1.35, False]
    out = [(t, w, e) for t, (w, e) in merged.items()]
    out.sort(key=lambda x: (-x[1], -len(x[0]), x[0]))
    return out[:28]


def definition_line_for(symbol: str, text: str) -> bool:
    esc = re.escape(symbol)
    patterns = [
        rf"\bfunc\s+(?:\([^)]*\)\s*)?{esc}\b",       # Go
        rf"\bdef\s+{esc}\b",                          # Python
        rf"\bclass\s+{esc}\b",
        rf"\bfunction\s+{esc}\b",                     # JS/TS
        rf"\b(?:const|let|var)\s+{esc}\b",
        rf"\b(?:public|private|protected|static|final|synchronized|abstract|native|default)\b[^;{{}}]*\b{esc}\s*\(",
        rf"^\s*[A-Za-z_$][A-Za-z0-9_$<>?,\[\]. ]+\s+{esc}\s*\(",  # Java/C-like method
    ]
    return any(re.search(p, text) for p in patterns)


def exact_symbol_definition_files(by_file: dict[str, dict], prompt: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for symbol in prompt_symbols(prompt):
        low_symbol = symbol.lower()
        files = set()
        for path, rec in by_file.items():
            if prev.is_test_path(path) or not prev.ORIGINAL_IS_PROD(path):
                continue
            for _, text in rec.get("lines", []):
                if low_symbol in text.lower() and definition_line_for(symbol, text):
                    files.add(path)
                    break
        if files:
            result[symbol] = files
    return result


def certified_rank(by_file, terms):
    rows = ORIGINAL_SMART_RANK(by_file, terms)
    unique_defs = []
    for symbol, files in exact_symbol_definition_files(by_file, prev.CURRENT_PROMPT).items():
        if len(files) == 1:
            unique_defs.append((symbol, next(iter(files))))
    if unique_defs:
        # A file may define multiple named prompt symbols. More unique-symbol proofs win.
        counts = {}
        for symbol, path in unique_defs:
            counts.setdefault(path, []).append(symbol)
        for row in rows:
            if row["path"] in counts:
                row["score"] += 10_000.0 + 1_000.0 * len(counts[row["path"]])
                row["certified_symbols"] = counts[row["path"]]
    rows.sort(key=lambda r: (-r["score"], -r["exact_hits"], r["hit_bytes"], r["path"]))
    return rows


base.query_terms = expanded_query
base.rank_files = certified_rank

if __name__ == "__main__":
    base.main()
