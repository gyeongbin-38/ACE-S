#!/usr/bin/env python3
"""Second execution-only optimization for the frozen v0.5 minimality grid.

Adds memoization of candidate window features by (source-lines object, span) on
top of v0.5.1's source/support cache. Selection equations, scoring, grid, and
winner ordering are unchanged. v0.5.1 still cross-checks one card for every
WindowCfg against the original implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import search_repo_behavior_witness_minimality_v051_cached as cached  # noqa: E402

behavior = cached.behavior
_candidate_cache: dict[tuple[int, int], list[dict]] = {}


def _candidate_features(lines: list[str], supports: list[dict[int, float]], span: int) -> list[dict]:
    key = (id(lines), span)
    features = _candidate_cache.get(key)
    if features is not None:
        return features

    features = []
    for start, end in behavior.candidate_windows(lines, supports, span):
        per_term, structural, density, byte_cost = behavior.window_features(
            lines, supports, start, end
        )
        if not per_term:
            continue
        features.append(
            {
                "start": start,
                "end": end,
                "per_term": per_term,
                "structural": structural,
                "density": density,
                "bytes": byte_cost,
            }
        )
    _candidate_cache[key] = features
    return features


def _choose_windows_span_cached(
    lines: list[str], supports: list[dict[int, float]], cfg: behavior.WindowCfg
) -> list[tuple[int, int]]:
    # The candidate dictionaries are immutable during selection; only the local
    # list of remaining references and the local covered set change.
    remaining = list(_candidate_features(lines, supports, cfg.span))
    selected: list[dict] = []
    covered: set[int] = set()

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


def main() -> None:
    cached._choose_windows_cached = _choose_windows_span_cached
    cached.main()


if __name__ == "__main__":
    main()
