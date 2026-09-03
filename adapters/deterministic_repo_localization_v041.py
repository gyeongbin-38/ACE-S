#!/usr/bin/env python3
"""Freeze-candidate adapter: v0.3 scorer + exact-symbol definition certificate only.

No weak morphology/prefix expansion is included because that development
experiment regressed a previously correct task. The proof-like symbol rule
abstains unless an explicitly named code-like prompt symbol has exactly one
production definition in the retrieved evidence.
"""
from __future__ import annotations

import re

import deterministic_repo_localization_v03 as prev
import deterministic_repo_localization as base

ORIGINAL_SMART_RANK = prev.smart_rank_files


def prompt_symbols(prompt: str) -> list[str]:
    out = []
    for tok in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", prompt):
        if "_" in tok or any(c.isupper() for c in tok[1:]):
            out.append(tok)
    return list(dict.fromkeys(out))


def definition_line_for(symbol: str, text: str) -> bool:
    esc = re.escape(symbol)
    patterns = [
        rf"\bfunc\s+(?:\([^)]*\)\s*)?{esc}\b",
        rf"\bdef\s+{esc}\b",
        rf"\bclass\s+{esc}\b",
        rf"\bfunction\s+{esc}\b",
        rf"\b(?:const|let|var)\s+{esc}\b",
        rf"\b(?:public|private|protected|static|final|synchronized|abstract|native|default)\b[^;{{}}]*\b{esc}\s*\(",
        rf"^\s*[A-Za-z_$][A-Za-z0-9_$<>?,\[\]. ]+\s+{esc}\s*\(",
    ]
    return any(re.search(p, text) for p in patterns)


def certified_definition_paths(by_file: dict[str, dict], prompt: str) -> dict[str, list[str]]:
    result = {}
    for symbol in prompt_symbols(prompt):
        low_symbol = symbol.lower()
        files = []
        for path, rec in by_file.items():
            if prev.is_test_path(path) or not prev.ORIGINAL_IS_PROD(path):
                continue
            if any(low_symbol in text.lower() and definition_line_for(symbol, text) for _, text in rec.get("lines", [])):
                files.append(path)
        if len(set(files)) == 1:
            result[symbol] = list(dict.fromkeys(files))
    return result


def certified_rank(by_file, terms):
    rows = ORIGINAL_SMART_RANK(by_file, terms)
    proofs = certified_definition_paths(by_file, prev.CURRENT_PROMPT)
    by_path: dict[str, list[str]] = {}
    for symbol, files in proofs.items():
        for path in files:
            by_path.setdefault(path, []).append(symbol)
    for row in rows:
        if row["path"] in by_path:
            row["score"] += 10_000.0 + 1_000.0 * len(by_path[row["path"]])
            row["certified_symbols"] = by_path[row["path"]]
    rows.sort(key=lambda r: (-r["score"], -r["exact_hits"], r["hit_bytes"], r["path"]))
    return rows


base.rank_files = certified_rank

if __name__ == "__main__":
    base.main()
