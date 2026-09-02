#!/usr/bin/env python3
"""Development v2 search for tail-safe sequential rollout racing.

Mean-only development gates failed to predict sealed tail risk for both margin-
and agreement-based early stopping. This search therefore imposes three gates
before compute savings matter:

1. mean environment degradation <= +1%
2. p90 per-world environment degradation <= +5%
3. >=90% of worlds are within +1% of fixed K=8

Only after all three Quality-First gates pass do we maximize rollout-compute
reduction. Development only; freeze before any fresh sealed OOD generator.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import asdict

from discover_sequential_rollout_racing import DEV_SEED, RacingPolicy, evaluate, policies
from run_context_action_dominance_bench import gen_world

WORLDS = 360
MEAN_GATE = 0.01
P90_GATE = 0.05
WITHIN_1PCT_GATE = 0.90


def quantile(values, q):
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def main():
    rng = random.Random(DEV_SEED + 17_003)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = [gen_world(rng.randrange(1_000_000_000), families[i % len(families)]) for i in range(WORLDS)]

    valid = []
    for i, world in enumerate(worlds):
        seed = DEV_SEED + 17_003 + i * 67
        base_e, base_c = evaluate(world, seed, None)
        if math.isfinite(base_e) and math.isfinite(base_c):
            valid.append((i, world, seed, base_e, base_c))

    base_e_mean = statistics.fmean(x[3] for x in valid)
    base_c_mean = statistics.fmean(x[4] for x in valid)
    rows = []
    for policy in policies():
        envs = []
        comps = []
        deltas = []
        for _i, world, seed, base_e, _base_c in valid:
            e, c = evaluate(world, seed, policy)
            envs.append(e)
            comps.append(c)
            deltas.append(e / base_e - 1.0)
        mean_e = statistics.fmean(envs)
        mean_c = statistics.fmean(comps)
        mean_delta = mean_e / base_e_mean - 1.0
        p90_delta = quantile(deltas, 0.90)
        within1 = sum(d <= 0.01 + 1e-12 for d in deltas) / len(deltas)
        compute_reduction = 1.0 - mean_c / base_c_mean
        eligible = (
            mean_delta <= MEAN_GATE + 1e-12
            and p90_delta <= P90_GATE + 1e-12
            and within1 >= WITHIN_1PCT_GATE - 1e-12
        )
        rows.append((policy, eligible, mean_delta, p90_delta, within1, max(deltas), compute_reduction, mean_e, mean_c))

    eligible_rows = [r for r in rows if r[1]]
    eligible_rows.sort(key=lambda r: (r[6], -r[3], r[4]), reverse=True)
    winner = eligible_rows[0] if eligible_rows else None

    def compact(row):
        policy, _ok, mean_delta, p90_delta, within1, max_delta, compute, mean_e, mean_c = row
        return {
            "policy": asdict(policy),
            "mean_environment_change_pct": round(100 * mean_delta, 3),
            "p90_world_environment_change_pct": round(100 * p90_delta, 3),
            "max_world_environment_change_pct": round(100 * max_delta, 3),
            "within_1pct_world_rate_pct": round(100 * within1, 3),
            "rollout_compute_reduction_pct": round(100 * compute, 3),
            "mean_environment_cost": round(mean_e, 6),
            "mean_rollout_samples": round(mean_c, 3),
        }

    result = {
        "experiment": "sequential-rollout-racing-development-v0.2-tail-gated",
        "status": "development_only",
        "worlds": len(valid),
        "candidate_policies": len(rows),
        "quality_gates": {
            "mean_environment_degradation_max_pct": 1.0,
            "p90_world_degradation_max_pct": 5.0,
            "within_1pct_world_rate_min_pct": 90.0,
        },
        "fixed_k8": {
            "mean_environment_cost": round(base_e_mean, 6),
            "mean_rollout_samples": round(base_c_mean, 3),
        },
        "eligible_policies": len(eligible_rows),
        "selected": compact(winner) if winner else None,
        "top_eligible": [compact(r) for r in eligible_rows[:10]],
        "best_mean_only_but_tail_rejected": [
            compact(r)
            for r in sorted(
                [r for r in rows if r[2] <= MEAN_GATE + 1e-12 and not r[1]],
                key=lambda r: r[6],
                reverse=True,
            )[:5]
        ],
        "guardrail": "Development-only search. These tail gates were fixed before this script was first executed. If a policy passes, freeze it before introducing any new OOD families/seed; do not tune on sealed outcomes.",
        "claim_boundary": "Synthetic controller rollout economics. Empirical racing intervals are heuristics, and passing these development gates does not establish end-to-end LLM quality equivalence.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
