#!/usr/bin/env python3
"""v0.6 development experiment: make direct proof authority explicit.

Only the proof fast-path changes. Retrieval, ranking, frontier composition, and
Behavior Window policy remain unchanged. Opened Suite A v0.1 is development
evidence for this new lineage and is never counted as unseen again.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_minimality_v05 as fixed  # noqa: E402

DEV_MANIFEST = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-development-v0.5.json"
OPENED_SUITE_A = ROOT / "benchmarks/runtime-traces/sealed/repo-behavior-witness-suite-a-v0.1.json"

CUES = r"(?:function|method|class|property|utility|symbol|implement(?:ing|ation(?:\s+of)?)|contain(?:ing|s)|called|named)"
CODELIKE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def explicit_owner_symbols(prompt: str) -> list[str]:
    found: list[str] = []
    # Examples: "implementing findCaseInsensitivePathRec", "containing the
    # floatSafeRemainder utility", "property orderby_issubset_groupby".
    pattern = re.compile(
        rf"\b{CUES}\b(?:\s+the)?\s+[`'\"]?([A-Za-z_][A-Za-z0-9_.]*)[`'\"]?",
        re.IGNORECASE,
    )
    for m in pattern.finditer(prompt):
        symbol = m.group(1)
        if not CODELIKE.match(symbol):
            continue
        # Authority is only useful for code-like identifiers, not ordinary prose.
        if "_" not in symbol and "." not in symbol and not any(c.isupper() for c in symbol[1:]):
            continue
        if symbol not in found:
            found.append(symbol)
    return found


def safe_direct_proof(by_file: dict[str, dict], prompt: str):
    allowed = set(explicit_owner_symbols(prompt))
    if not allowed:
        return None, []
    proofs = fixed.rank_v041.certified_definition_paths(by_file, prompt)
    paths: list[str] = []
    symbols: list[str] = []
    for symbol, files in proofs.items():
        if symbol not in allowed or len(files) != 1:
            continue
        paths.append(files[0])
        symbols.append(symbol)
    unique = sorted(set(paths))
    if len(unique) == 1:
        return unique[0], sorted(symbols)
    return None, []


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(manifest: dict) -> dict:
    cached = fixed.build_cache(manifest)
    rows = []
    false_direct = 0
    frontier_hits = 0
    direct_count = 0
    for item in cached:
        t = item["task"]
        expected = t["expected_file"]
        direct = item["proof_path"]
        if direct is not None:
            direct_count += 1
            if direct != expected:
                false_direct += 1
        hit = expected in [r["path"] for r in item["frontier"]]
        frontier_hits += int(hit)
        rows.append({
            "task_id": t["task_id"],
            "direct_path": direct,
            "frontier_hit": hit,
            "frontier": [r["path"] for r in item["frontier"]],
        })
    return {
        "tasks": len(rows),
        "direct_count": direct_count,
        "false_direct": false_direct,
        "frontier_hits": frontier_hits,
        "rows": rows,
    }


def main() -> None:
    original = fixed.old.direct_proof
    fixed.old.direct_proof = safe_direct_proof
    try:
        dev = evaluate(load(DEV_MANIFEST))
        suite_a = evaluate(load(OPENED_SUITE_A))
    finally:
        fixed.old.direct_proof = original
    print(json.dumps({
        "experiment": "direct-proof-authority-gate-v0.6",
        "status": "development_only_after_suite_a_v01_opened",
        "change": "explicit target-ownership cue required before definition certificate may create direct selection",
        "development14": dev,
        "opened_suite_a6": suite_a,
        "success_gate": {
            "false_direct_total_eq_0": dev["false_direct"] + suite_a["false_direct"] == 0,
            "development14_frontier_eq_14": dev["frontier_hits"] == 14,
            "suite_a_frontier_not_regressed": suite_a["frontier_hits"] >= 4
        },
        "claim_boundary": "Proof-authority experiment only. Opened Suite A is development evidence. No unseen claim."
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
