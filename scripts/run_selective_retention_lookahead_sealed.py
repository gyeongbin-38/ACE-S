#!/usr/bin/env python3
"""Sealed OOD evaluation for frozen selective retention lookahead v0.2.

The trigger was frozen before these lifecycle families and seed were introduced.
Compare always-depth1, always-depth3, and frozen selective depth1/depth3.

Synthetic lifecycle economics only.
"""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict

import discover_retention_scheduler as ret
from discover_retention_lookahead_depth import rollout_cost
from discover_selective_retention_lookahead_v2 import Trigger, fires

FREEZE_COMMIT = "9fc9a5d91c2b08cf92bdc81282fd01490e217e97"
ALGORITHM_REF = "8909dab6f8f8af4380628ebe1bc4203d71e83191"
SEALED_SEED = 118_330_417
ITEMS_PER_FAMILY = 55
SIGMAS = (0.0, 0.5, 1.0)
NOISE_SEEDS = (118_330_431, 118_330_449)
FROZEN_TRIGGER = Trigger(
    quiet_threshold=0.08,
    min_quiet_steps=2,
    score_threshold=6.0,
    max_future_exact_rate=0.55,
)
FAMILIES = (
    "triple_revival",
    "quiet_semantic_revival",
    "exact_obvious_return",
    "no_revival",
    "short_idle_return",
    "cost_regime_shift",
)


def clamp(x, lo=0.01, hi=0.98):
    return min(hi, max(lo, x))


def make_item(rng: random.Random, family: str) -> ret.Item:
    horizon = rng.randint(11, 18)
    p_need = [rng.uniform(0.015, 0.10) for _ in range(horizon)]
    p_exact = [rng.uniform(0.10, 0.50) for _ in range(horizon)]

    if family == "triple_revival":
        centers = sorted(rng.sample(range(2, horizon - 1), 3))
        for c in centers:
            for t in range(max(0, c - 1), min(horizon, c + 2)):
                p_need[t] = max(p_need[t], rng.uniform(0.45, 0.88))
                p_exact[t] = rng.uniform(0.10, 0.50)

    elif family == "quiet_semantic_revival":
        start = rng.randint(horizon // 2, horizon - 3)
        for t in range(max(0, start - 4), start):
            p_need[t] = rng.uniform(0.01, 0.055)
        for t in range(start, horizon):
            p_need[t] = rng.uniform(0.55, 0.92)
            p_exact[t] = rng.uniform(0.03, 0.24)

    elif family == "exact_obvious_return":
        start = rng.randint(horizon // 2, horizon - 3)
        for t in range(max(0, start - 4), start):
            p_need[t] = rng.uniform(0.01, 0.055)
        for t in range(start, horizon):
            p_need[t] = rng.uniform(0.58, 0.94)
            p_exact[t] = rng.uniform(0.82, 0.98)

    elif family == "no_revival":
        p_need = [rng.uniform(0.01, 0.12) * (0.93 ** t) for t in range(horizon)]
        p_exact = [rng.uniform(0.05, 0.45) for _ in range(horizon)]

    elif family == "short_idle_return":
        start = rng.randint(4, horizon - 4)
        for t in range(max(0, start - 2), start):
            p_need[t] = rng.uniform(0.01, 0.06)
        for t in range(start, min(horizon, start + rng.randint(2, 4))):
            p_need[t] = rng.uniform(0.48, 0.85)
            p_exact[t] = rng.uniform(0.15, 0.55)

    elif family == "cost_regime_shift":
        start = rng.randint(horizon // 2, horizon - 3)
        for t in range(max(0, start - 3), start):
            p_need[t] = rng.uniform(0.01, 0.07)
        for t in range(start, horizon):
            p_need[t] = rng.uniform(0.35, 0.78)
            p_exact[t] = rng.uniform(0.10, 0.48)

    reacquire = rng.uniform(2.5, 9.0)
    raw_hold = rng.uniform(0.18, 0.9)
    abstract_hold = raw_hold * rng.uniform(0.05, 0.24)
    compact = rng.uniform(0.12, 1.2)
    abstract_failure = rng.uniform(0.03, 0.28)

    if family in {"triple_revival", "quiet_semantic_revival", "cost_regime_shift"}:
        reacquire *= rng.uniform(1.3, 2.5)
    if family == "no_revival":
        raw_hold *= rng.uniform(1.2, 1.8)
    if family == "cost_regime_shift":
        raw_hold *= rng.uniform(0.7, 1.4)

    return ret.Item(
        tuple(clamp(x) for x in p_need),
        tuple(clamp(x) for x in p_exact),
        raw_hold,
        abstract_hold,
        reacquire,
        compact,
        clamp(abstract_failure, 0.01, 0.70),
        family,
    )


def main():
    rng = random.Random(SEALED_SEED)
    items = []
    iid = 0
    for family in FAMILIES:
        for _ in range(ITEMS_PER_FAMILY):
            item = make_item(rng, family)
            items.append((iid, item, ret.optimal_cost(item), family))
            iid += 1

    selected_ids = {iid for iid, item, _opt, _family in items if fires(item, FROZEN_TRIGGER)}
    d1_vals, d3_vals, sel_vals = [], [], []
    by_family = defaultdict(lambda: {"d1": [], "d3": [], "sel": [], "ids": set()})

    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                d1 = rollout_cost(item, iid, sigma, nseed, 1) / opt
                d3 = rollout_cost(item, iid, sigma, nseed, 3) / opt
                sel = d3 if iid in selected_ids else d1
                d1_vals.append(d1); d3_vals.append(d3); sel_vals.append(sel)
                row = by_family[family]
                row["d1"].append(d1); row["d3"].append(d3); row["sel"].append(sel); row["ids"].add(iid)

    d1_mean = statistics.fmean(d1_vals)
    d3_mean = statistics.fmean(d3_vals)
    sel_mean = statistics.fmean(sel_vals)
    full_gain = d1_mean - d3_mean
    selected_gain = d1_mean - sel_mean
    capture = selected_gain / full_gain if full_gain > 1e-12 else 1.0
    invocation = len(selected_ids) / len(items)

    family_out = {}
    for family, row in sorted(by_family.items()):
        family_item_ids = {iid for iid, _item, _opt, fam in items if fam == family}
        family_out[family] = {
            "items": len(family_item_ids),
            "depth3_item_rate_pct": round(100 * len(family_item_ids & selected_ids) / len(family_item_ids), 3),
            "depth1_mean": round(statistics.fmean(row["d1"]), 5),
            "depth3_mean": round(statistics.fmean(row["d3"]), 5),
            "selective_mean": round(statistics.fmean(row["sel"]), 5),
        }

    obvious_max = max(
        family_out["exact_obvious_return"]["depth3_item_rate_pct"],
        family_out["no_revival"]["depth3_item_rate_pct"],
    )
    result = {
        "experiment": "selective-retention-lookahead-sealed-ood-v0.2",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "algorithm_ref": ALGORITHM_REF,
        "sealed_seed": SEALED_SEED,
        "families": list(FAMILIES),
        "items": len(items),
        "evaluations_per_condition": len(d1_vals),
        "frozen_trigger": {
            "quiet_threshold": FROZEN_TRIGGER.quiet_threshold,
            "min_quiet_steps": FROZEN_TRIGGER.min_quiet_steps,
            "score_threshold": FROZEN_TRIGGER.score_threshold,
            "max_future_exact_rate": FROZEN_TRIGGER.max_future_exact_rate,
        },
        "always_depth1_mean": round(d1_mean, 6),
        "always_depth3_mean": round(d3_mean, 6),
        "selective_mean": round(sel_mean, 6),
        "depth3_item_rate_pct": round(100 * invocation, 3),
        "mean_cost_reduction_vs_depth1_pct": round(100 * selected_gain / d1_mean, 3),
        "fraction_of_always_depth3_gain_captured_pct": round(100 * capture, 3),
        "by_family": family_out,
        "sealed_gate": {
            "beats_always_depth1": sel_mean < d1_mean - 1e-12,
            "captures_at_least_75pct_depth3_gain": capture >= 0.75 - 1e-12,
            "depth3_item_rate_le_40pct": invocation <= 0.40 + 1e-12,
            "obvious_exact_or_no_revival_depth3_rate_le_20pct": obvious_max <= 20.0 + 1e-12,
        },
        "claim_boundary": "Frozen trigger on post-freeze synthetic lifecycle families and seed. The trigger sees generator-level future need/exactness probabilities; real deployment requires calibrated estimates. Not end-to-end LLM quality evidence.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
