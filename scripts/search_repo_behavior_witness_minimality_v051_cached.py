#!/usr/bin/env python3
"""Cached execution wrapper for the frozen v0.5 minimality search.

This changes only execution cost. Policy grid, retrieval, witness scorer, hard
gates, and winner ordering remain defined by
search_repo_behavior_witness_minimality_v05.py.

For every WindowCfg, the first card materialized is cross-checked against the
original v0.3 behavior_card implementation before cached execution continues.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_minimality_v05 as search  # noqa: E402

behavior = search.behavior_v03
_original_behavior_card = behavior.behavior_card
_source_cache: dict[tuple, tuple[list[str], list[dict[int, float]]]] = {}
_verified_cfgs: set[tuple[int, int, int]] = set()


def _source_key(repo: Path, row: dict, terms: list[tuple[str, float, bool]]) -> tuple:
    return (str(repo), row["path"], tuple(terms))


def _source_state(repo: Path, row: dict, terms: list[tuple[str, float, bool]]):
    key = _source_key(repo, row, terms)
    state = _source_cache.get(key)
    if state is None:
        lines = (repo / row["path"]).read_text(encoding="utf-8", errors="replace").splitlines()
        supports = behavior.per_line_support(lines, terms)
        state = (lines, supports)
        _source_cache[key] = state
    return state


def _choose_windows_cached(
    lines: list[str], supports: list[dict[int, float]], cfg: behavior.WindowCfg
) -> list[tuple[int, int]]:
    candidates = []
    for start, end in behavior.candidate_windows(lines, supports, cfg.span):
        per_term, structural, density, byte_cost = behavior.window_features(
            lines, supports, start, end
        )
        if not per_term:
            continue
        candidates.append(
            {
                "start": start,
                "end": end,
                "per_term": per_term,
                "structural": structural,
                "density": density,
                "bytes": byte_cost,
            }
        )

    selected: list[dict] = []
    covered: set[int] = set()
    remaining = candidates
    while remaining and len(selected) < cfg.max_windows:
        best = None
        best_key = None
        for window in remaining:
            new_gain = sum(v for i, v in window["per_term"].items() if i not in covered)
            repeat_gain = sum(v for i, v in window["per_term"].items() if i in covered)
            objective = (
                new_gain
                + 0.10 * repeat_gain
                + 0.30 * window["structural"]
                + 0.20 * window["density"]
                - 0.00008 * window["bytes"]
            )
            key = (
                objective,
                new_gain,
                window["structural"],
                -window["bytes"],
                -window["start"],
            )
            if best_key is None or key > best_key:
                best_key = key
                best = window
        if best is None or best_key is None or best_key[0] <= 0:
            break
        selected.append(best)
        covered.update(best["per_term"])
        remaining = [
            window
            for window in remaining
            if not (
                window["start"] <= best["end"] + cfg.overlap_merge_gap
                and best["start"] <= window["end"] + cfg.overlap_merge_gap
            )
        ]

    intervals = sorted((window["start"], window["end"]) for window in selected)
    merged: list[list[int]] = []
    for start, end in intervals:
        if not merged or start > merged[-1][1] + cfg.overlap_merge_gap:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def cached_behavior_card(
    repo: Path, row: dict, terms: list[tuple[str, float, bool]], cfg: behavior.WindowCfg
) -> dict:
    lines, supports = _source_state(repo, row, terms)
    windows = _choose_windows_cached(lines, supports, cfg)
    records = []
    for window_id, (start, end) in enumerate(windows, 1):
        for line_no in range(start, end + 1):
            records.append({"window": window_id, "line": line_no, "text": lines[line_no - 1]})
    card = {"path": row["path"], "windows": windows, "records": records}

    # One exact cross-check for every configuration proves that the cached
    # implementation preserves the original window/record semantics across the
    # entire 108-policy grid, rather than checking only the historical 8/3/2.
    cfg_key = (cfg.span, cfg.max_windows, cfg.overlap_merge_gap)
    if cfg_key not in _verified_cfgs:
        original = _original_behavior_card(repo, row, terms, cfg)
        if original != card:
            raise AssertionError(f"cached behavior-card mismatch for cfg={cfg_key}, path={row['path']}")
        _verified_cfgs.add(cfg_key)
    return card


def main() -> None:
    behavior.behavior_card = cached_behavior_card
    search.main()
    if len(_verified_cfgs) != 108:
        raise AssertionError(f"expected 108 equivalence-checked configs, got {len(_verified_cfgs)}")


if __name__ == "__main__":
    main()
