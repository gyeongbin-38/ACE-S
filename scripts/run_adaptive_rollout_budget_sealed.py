#!/usr/bin/env python3
"""Sealed OOD test for the frozen adaptive rollout-budget policy.

The policy was frozen before these world families and this sealed seed were
introduced. This test compares the frozen adaptive budget against fixed K=8,
both after the same structural-dominance pruning.

Synthetic controller mechanics only; not end-to-end LLM evidence.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict

from discover_adaptive_rollout_budget_v2 import Policy, evaluate
from run_context_action_dominance_bench import World

FREEZE_COMMIT = "6fc4a021c692f901470b239611a1921dc0f4a26e"
SEALED_SEED = 12_440_771
WORLDS_PER_FAMILY = 55
FROZEN_POLICY = Policy(
    greedy_margin=5.0,
    small_margin=1.05,
    small_k=4,
    medium_k=6,
    hard_k=8,
)
FAMILIES = (
    "near_tie_dense",
    "rare_decisive",
    "asymmetric_prior",
    "deep_chain",
    "misleading_frontier",
    "redundant_refinement",
)


def normalize(xs):
    z = sum(xs)
    return [x / z for x in xs]


def random_partition(rng: random.Random, n: int, k: int):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def add_action(actions, cost, outcomes):
    actions.append({"cost": float(cost), "outcomes": tuple(outcomes)})


def gen_sealed_world(seed: int, family: str) -> World:
    rng = random.Random(seed)
    n = rng.randint(6, 9)
    dcount = rng.choice([2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d

    if family == "asymmetric_prior":
        dominant = rng.randrange(n)
        raw = [rng.uniform(0.02, 0.15) for _ in range(n)]
        raw[dominant] = rng.uniform(2.5, 5.0)
    elif family == "rare_decisive":
        raw = [rng.uniform(0.5, 1.5) for _ in range(n)]
        rare = rng.randrange(n)
        raw[rare] *= rng.uniform(0.03, 0.12)
    else:
        raw = [rng.gammavariate(rng.uniform(0.5, 2.2), 1.0) for _ in range(n)]
    priors = normalize(raw)

    actions = []

    if family == "near_tie_dense":
        # Many similarly priced candidates produce small score margins and test
        # whether the adaptive policy correctly spends more compute.
        base_cost = rng.uniform(1.3, 2.1)
        for _ in range(rng.randint(10, 14)):
            add_action(
                actions,
                base_cost * rng.uniform(0.88, 1.12),
                random_partition(rng, n, rng.choice([2, 3, 4])),
            )

    elif family == "rare_decisive":
        # Several broad, attractive partitions plus a less obvious decision-
        # relevant probe whose value is concentrated on a low-prior state.
        for _ in range(rng.randint(7, 10)):
            add_action(actions, rng.uniform(0.7, 2.0), random_partition(rng, n, rng.choice([2, 3])))
        rare_idx = min(range(n), key=lambda i: priors[i])
        rare_probe = [0] * n
        rare_probe[rare_idx] = 1
        add_action(actions, rng.uniform(0.8, 1.6), rare_probe)

    elif family == "asymmetric_prior":
        # Cheap coarse probes mostly resolve high-mass states; a more expensive
        # exact decision observation protects the low-mass tail.
        for _ in range(rng.randint(6, 9)):
            add_action(actions, rng.uniform(0.4, 1.4), random_partition(rng, n, 2))
        for _ in range(3):
            add_action(actions, rng.uniform(1.5, 3.2), random_partition(rng, n, rng.choice([3, 4])))

    elif family == "deep_chain":
        # Build mostly binary probes so useful decisions often require several
        # sequential observations rather than one direct high-information call.
        for bit in range(4):
            outcomes = tuple((i >> bit) & 1 for i in range(n))
            if len(set(outcomes)) > 1:
                add_action(actions, rng.uniform(0.45, 1.1), outcomes)
        for _ in range(5):
            add_action(actions, rng.uniform(0.8, 1.8), random_partition(rng, n, 2))

    elif family == "misleading_frontier":
        # High-entropy state partitions can be weak for the actual decision.
        # Add them cheaply, then add a few decision-aligned but less flashy probes.
        for _ in range(rng.randint(7, 10)):
            outcomes = list(range(n))
            rng.shuffle(outcomes)
            k = rng.choice([3, 4])
            outcomes = tuple(x % k for x in outcomes)
            add_action(actions, rng.uniform(0.6, 1.4), outcomes)
        for d in range(dcount):
            aligned = tuple(1 if x == d else 0 for x in decisions)
            if len(set(aligned)) > 1:
                add_action(actions, rng.uniform(1.0, 2.0), aligned)

    elif family == "redundant_refinement":
        bases = []
        for _ in range(rng.randint(5, 7)):
            outcomes = random_partition(rng, n, rng.choice([2, 3, 4]))
            cost = rng.uniform(0.6, 2.0)
            add_action(actions, cost, outcomes)
            bases.append((cost, outcomes))
        # Add expensive duplicates and coarser variants so structural pruning is
        # heavily exercised before the adaptive-compute layer runs.
        for _ in range(rng.randint(10, 16)):
            cost, outcomes = rng.choice(bases)
            variant = list(outcomes)
            if rng.random() < 0.55:
                vals = sorted(set(variant))
                if len(vals) >= 2:
                    src, dst = rng.sample(vals, 2)
                    variant = [dst if x == src else x for x in variant]
            add_action(actions, cost * rng.uniform(1.05, 2.7), variant)

    # Always provide a direct decision-relevant action, but vary its cost enough
    # that a multi-step path can still be preferable.
    add_action(actions, rng.uniform(1.8, 5.5), tuple(decisions))
    return World(priors, decisions, actions, family)


def pct(values, p):
    xs = sorted(values)
    if not xs:
        return float("nan")
    pos = (len(xs) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def summarize_delta(values):
    return {
        "mean_pct": round(100 * statistics.fmean(values), 3),
        "median_pct": round(100 * statistics.median(values), 3),
        "p90_pct": round(100 * pct(values, 0.90), 3),
        "max_pct": round(100 * max(values), 3),
    }


def main():
    rng = random.Random(SEALED_SEED)
    rows = []
    by_family = defaultdict(list)
    for family in FAMILIES:
        for j in range(WORLDS_PER_FAMILY):
            world_seed = rng.randrange(1_000_000_000)
            world = gen_sealed_world(world_seed, family)
            eval_seed = SEALED_SEED + len(rows) * 73 + 19
            fixed_env, fixed_comp = evaluate(world, eval_seed, None)
            adapt_env, adapt_comp = evaluate(world, eval_seed, FROZEN_POLICY)
            if not all(math.isfinite(x) for x in (fixed_env, fixed_comp, adapt_env, adapt_comp)):
                continue
            env_delta = adapt_env / fixed_env - 1.0
            compute_reduction = 1.0 - adapt_comp / fixed_comp if fixed_comp > 0 else 0.0
            item = (family, env_delta, compute_reduction, fixed_env, adapt_env, fixed_comp, adapt_comp)
            rows.append(item)
            by_family[family].append(item)

    env_deltas = [r[1] for r in rows]
    compute_reductions = [r[2] for r in rows]
    fixed_env_mean = statistics.fmean(r[3] for r in rows)
    adapt_env_mean = statistics.fmean(r[4] for r in rows)
    fixed_comp_mean = statistics.fmean(r[5] for r in rows)
    adapt_comp_mean = statistics.fmean(r[6] for r in rows)

    result = {
        "experiment": "adaptive-rollout-budget-sealed-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "families": list(FAMILIES),
        "worlds_evaluated": len(rows),
        "frozen_policy": {
            "greedy_margin": FROZEN_POLICY.greedy_margin,
            "small_margin": FROZEN_POLICY.small_margin,
            "small_k": FROZEN_POLICY.small_k,
            "medium_k": FROZEN_POLICY.medium_k,
            "hard_k": FROZEN_POLICY.hard_k,
        },
        "fixed_k8": {
            "mean_environment_cost": round(fixed_env_mean, 6),
            "mean_rollout_samples": round(fixed_comp_mean, 3),
        },
        "adaptive": {
            "mean_environment_cost": round(adapt_env_mean, 6),
            "mean_rollout_samples": round(adapt_comp_mean, 3),
        },
        "mean_environment_cost_change_pct": round(100 * (adapt_env_mean / fixed_env_mean - 1.0), 3),
        "environment_delta_distribution": summarize_delta(env_deltas),
        "mean_rollout_compute_reduction_pct": round(100 * (1.0 - adapt_comp_mean / fixed_comp_mean), 3),
        "adaptive_no_worse_world_rate_pct": round(100 * sum(x <= 1e-12 for x in env_deltas) / len(env_deltas), 3),
        "adaptive_within_1pct_world_rate_pct": round(100 * sum(x <= 0.01 + 1e-12 for x in env_deltas) / len(env_deltas), 3),
        "by_family": {
            family: {
                "n": len(vals),
                "mean_environment_change_pct": round(100 * (statistics.fmean(v[4] for v in vals) / statistics.fmean(v[3] for v in vals) - 1.0), 3),
                "mean_compute_reduction_pct": round(100 * (1.0 - statistics.fmean(v[6] for v in vals) / statistics.fmean(v[5] for v in vals)), 3),
                "within_1pct_world_rate_pct": round(100 * sum(v[1] <= 0.01 + 1e-12 for v in vals) / len(vals), 3),
            }
            for family, vals in sorted(by_family.items())
        },
        "sealed_gate": {
            "mean_environment_degradation_le_1pct": (adapt_env_mean / fixed_env_mean - 1.0) <= 0.01 + 1e-12,
            "mean_compute_reduction_positive": adapt_comp_mean < fixed_comp_mean,
        },
        "claim_boundary": "Post-freeze synthetic OOD evaluation against fixed K=8 after identical structural pruning. The new families are post-freeze but were authored within the same project; this is not an independently curated external benchmark or end-to-end LLM quality test.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
