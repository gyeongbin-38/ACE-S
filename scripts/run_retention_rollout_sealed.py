#!/usr/bin/env python3
"""Post-freeze sealed/OOD lifecycle test for the frozen retention rollout algorithm."""
from __future__ import annotations

import json
import math
import random
import statistics

import discover_retention_scheduler as ret
from run_retention_rollout_bench import retention_base_and_rollout, summarize

FREEZE_COMMIT = "a8277cbd83e8ef07cda7a99c93b50d720328ee00"
SEALED_SEED = 9_144_731
NOISE_SEEDS = [9_144_743, 9_144_769, 9_144_787]
SIGMAS = [0.0, 0.5, 1.0]
ITEMS_PER_FAMILY = 55


def clamp(x, lo=0.01, hi=0.97):
    return min(hi, max(lo, x))


def make_item(rng: random.Random, family: str) -> ret.Item:
    horizon = rng.randint(7, 12)

    if family == "alternating_reuse":
        high = rng.uniform(0.55, 0.9)
        low = rng.uniform(0.02, 0.12)
        p_need = [high if t % 2 == 0 else low for t in range(horizon)]
        p_exact = [rng.uniform(0.2, 0.65) for _ in range(horizon)]
    elif family == "long_idle_revival":
        pivot = rng.randint(max(2, horizon // 2), horizon - 2)
        p_need = [rng.uniform(0.01, 0.08) for _ in range(horizon)]
        for t in range(pivot, horizon):
            p_need[t] = clamp(rng.uniform(0.55, 0.92))
        p_exact = [rng.uniform(0.15, 0.6) for _ in range(horizon)]
    elif family == "exactness_burst":
        p_need = [rng.uniform(0.2, 0.55) for _ in range(horizon)]
        pivot = rng.randrange(1, horizon - 1)
        p_exact = [rng.uniform(0.03, 0.18) for _ in range(horizon)]
        for t in range(max(0, pivot - 1), min(horizon, pivot + 2)):
            p_exact[t] = rng.uniform(0.82, 0.98)
    elif family == "semantic_then_exact":
        split = horizon // 2
        p_need = [rng.uniform(0.25, 0.7) for _ in range(horizon)]
        p_exact = [rng.uniform(0.03, 0.18) if t < split else rng.uniform(0.75, 0.97) for t in range(horizon)]
    elif family == "decay_then_revival":
        p_need = []
        for t in range(horizon):
            x = 0.72 * math.exp(-t / 2.0)
            if t >= horizon - 3:
                x += 0.55 * (t - (horizon - 4)) / 3.0
            p_need.append(clamp(x * rng.uniform(0.8, 1.2)))
        p_exact = [rng.uniform(0.1, 0.75) for _ in range(horizon)]
    elif family == "uncertain_revival":
        # Multiple possible late spikes without a regular period.
        spikes = set(rng.sample(range(1, horizon), k=min(3, horizon - 1)))
        p_need = [rng.uniform(0.03, 0.16) for _ in range(horizon)]
        for t in spikes:
            p_need[t] = rng.uniform(0.5, 0.9)
        p_exact = [rng.uniform(0.1, 0.8) for _ in range(horizon)]
    else:
        raise ValueError(family)

    reacquire = rng.uniform(2.5, 10.0)
    raw_hold = rng.uniform(0.16, 0.9)
    abstract_hold = raw_hold * rng.uniform(0.05, 0.3)
    compact_cost = rng.uniform(0.1, 1.4)
    abstract_failure = rng.uniform(0.02, 0.28)

    # Add family-specific economic stress without copying development families.
    if family == "long_idle_revival":
        reacquire *= rng.uniform(1.2, 2.0)
    if family == "semantic_then_exact":
        abstract_failure *= rng.uniform(0.7, 1.4)
    if family == "exactness_burst":
        raw_hold *= rng.uniform(0.8, 1.35)

    return ret.Item(
        tuple(p_need),
        tuple(p_exact),
        raw_hold,
        abstract_hold,
        reacquire,
        compact_cost,
        clamp(abstract_failure, 0.01, 0.75),
        family,
    )


def main():
    rng = random.Random(SEALED_SEED)
    families = [
        "alternating_reuse",
        "long_idle_revival",
        "exactness_burst",
        "semantic_then_exact",
        "decay_then_revival",
        "uncertain_revival",
    ]

    items = []
    iid = 0
    for family in families:
        for _ in range(ITEMS_PER_FAMILY):
            item = make_item(rng, family)
            opt = ret.optimal_cost(item)
            items.append((iid, item, opt, family))
            iid += 1

    base_vals = []
    rollout_vals = []
    by_family = {}
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                base, rollout = retention_base_and_rollout(item, iid, sigma, nseed)
                base_ratio = base / opt
                rollout_ratio = rollout / opt
                base_vals.append(base_ratio)
                rollout_vals.append(rollout_ratio)
                row = by_family.setdefault(family, {"base": [], "rollout": []})
                row["base"].append(base_ratio)
                row["rollout"].append(rollout_ratio)

    result = {
        "experiment": "retention-rollout-sealed-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "families": families,
        "items": len(items),
        "evaluations": len(rollout_vals),
        "sigmas": SIGMAS,
        "base_frozen_retention_policy": summarize(base_vals),
        "rollout_retention_policy": summarize(rollout_vals),
        "rollout_beats_or_ties_base_rate_pct": round(
            100.0 * sum(r <= b + 1e-12 for r, b in zip(rollout_vals, base_vals)) / len(base_vals), 3
        ),
        "mean_cost_reduction_vs_base_pct": round(
            100.0 * (1.0 - statistics.fmean(rollout_vals) / statistics.fmean(base_vals)), 3
        ),
        "by_family": {
            family: {name: summarize(vals) for name, vals in data.items()}
            for family, data in sorted(by_family.items())
        },
        "claim_boundary": (
            "Frozen retention rollout evaluated on lifecycle families and seed introduced after freeze. "
            "Synthetic expected lifecycle economics only. True need/exactness probabilities are available "
            "to the rollout evaluator; a real runtime must estimate them. Not end-to-end LLM quality evidence."
        ),
    }
    print(json.dumps(result, indent=2))

    assert result["rollout_beats_or_ties_base_rate_pct"] >= 99.0


if __name__ == "__main__":
    main()
