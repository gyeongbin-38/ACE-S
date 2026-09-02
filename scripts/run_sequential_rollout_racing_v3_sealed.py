#!/usr/bin/env python3
"""Sealed OOD test for frozen catastrophic-tail-safe sequential racing v0.3.

The policy was frozen before the seed and generator families in this file were
introduced. Do not tune min_rounds/z/gap using this result.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict

from discover_sequential_rollout_racing import RacingPolicy, evaluate
from run_context_action_dominance_bench import World

FREEZE_COMMIT = "19e3897c850830c20ba5809c30435d0bf64f3797"
SEALED_SEED = 609_441_227
WORLDS_PER_FAMILY = 80
POLICY = RacingPolicy(min_rounds=7, z=0.75, min_absolute_gap=0.0)
FAMILIES = (
    "near_tie_costs",
    "rare_expensive_branch",
    "many_similar_actions",
    "one_late_decisive",
    "heteroskedastic_costs",
    "dominance_sparse",
)


def normalize(xs):
    z = sum(xs)
    return tuple(x / z for x in xs)


def partition(rng, n, k):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def make_world(seed: int, family: str) -> World:
    rng = random.Random(seed)
    n = rng.randint(6, 9)
    dcount = rng.choice([2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d
    priors = list(normalize([rng.gammavariate(rng.uniform(.35, 2.2), 1.0) for _ in range(n)]))
    actions = []

    if family == "rare_expensive_branch":
        # Put small probability on one branch whose wrong first action creates a
        # large downstream penalty; designed to expose rare-tail misranking.
        rare = rng.randrange(n)
        priors = [rng.uniform(.8, 1.4) for _ in range(n)]
        priors[rare] = rng.uniform(.01, .04)
        priors = list(normalize(priors))

    base_count = rng.randint(8, 13)
    for i in range(base_count):
        if family == "near_tie_costs":
            cost = 1.0 + rng.uniform(-.08, .08)
        elif family == "heteroskedastic_costs":
            cost = math.exp(rng.uniform(math.log(.25), math.log(14.0)))
        else:
            cost = math.exp(rng.uniform(math.log(.4), math.log(5.5)))
        if family == "many_similar_actions" and i > 1:
            # Start from a small number of latent partitions and perturb only a
            # few observations, producing difficult near-equivalent candidates.
            base = partition(rng, n, rng.choice([2, 3])) if i < 3 else actions[rng.randrange(len(actions))]["outcomes"]
            out = list(base)
            if rng.random() < .55:
                j = rng.randrange(n)
                out[j] = (out[j] + 1) % max(2, len(set(out)))
            outcomes = tuple(out)
        else:
            outcomes = partition(rng, n, rng.choice([2, 2, 3, 4]))
        actions.append({"cost": float(cost), "outcomes": outcomes})

    # Guarantee at least one feasible complete action, but vary where its cost
    # sits to create both obvious and non-obvious first-step decisions.
    if family == "one_late_decisive":
        actions.append({"cost": rng.uniform(4.5, 8.0), "outcomes": tuple(decisions)})
        # Add cheap partial probes that can make the direct decision attractive
        # only after one observation.
        for _ in range(3):
            actions.append({"cost": rng.uniform(.25, .7), "outcomes": partition(rng, n, 2)})
    elif family == "rare_expensive_branch":
        actions.append({"cost": rng.uniform(1.0, 2.2), "outcomes": tuple(decisions)})
        # A tempting cheap probe whose rare branch remains hard.
        rare_map = [0 for _ in range(n)]
        rare_map[min(range(n), key=lambda i: priors[i])] = 1
        actions.append({"cost": rng.uniform(.12, .35), "outcomes": tuple(rare_map)})
    else:
        actions.append({"cost": rng.uniform(1.0, 4.5), "outcomes": tuple(decisions)})

    if family == "dominance_sparse":
        # Avoid deliberately duplicated/refining actions: the uncertain plane
        # must work after exact pruning has little to remove.
        pass
    elif family == "many_similar_actions":
        # Add cost-near duplicate candidates; dominance may remove some but not
        # all because costs/partitions differ slightly.
        for _ in range(5):
            src = actions[rng.randrange(len(actions)-1)]
            out = list(src["outcomes"])
            j = rng.randrange(n)
            out[j] = (out[j] + 1) % 3
            actions.append({"cost": src["cost"] * rng.uniform(.96, 1.08), "outcomes": tuple(out)})

    return World(priors, tuple(decisions), actions, family)


def quantile(vals, q):
    xs = sorted(vals)
    p = (len(xs) - 1) * q
    lo, hi = math.floor(p), math.ceil(p)
    return xs[lo] if lo == hi else xs[lo] * (hi - p) + xs[hi] * (p - lo)


def cvar_upper(vals, frac=.05):
    xs = sorted(vals, reverse=True)
    n = max(1, math.ceil(len(xs) * frac))
    return statistics.fmean(xs[:n])


def main():
    rng = random.Random(SEALED_SEED)
    rows = []
    by = defaultdict(list)
    for family in FAMILIES:
        for j in range(WORLDS_PER_FAMILY):
            world = make_world(rng.randrange(1_000_000_000), family)
            seed = SEALED_SEED + len(rows) * 131
            be, bc = evaluate(world, seed, None)
            ae, ac = evaluate(world, seed, POLICY)
            if not all(math.isfinite(x) for x in (be, bc, ae, ac)):
                continue
            delta = ae / be - 1.0
            comp_red = 1.0 - ac / bc if bc > 0 else 0.0
            row = (family, be, bc, ae, ac, delta, comp_red)
            rows.append(row)
            by[family].append(row)

    base_e = statistics.fmean(r[1] for r in rows)
    adapt_e = statistics.fmean(r[3] for r in rows)
    base_c = statistics.fmean(r[2] for r in rows)
    adapt_c = statistics.fmean(r[4] for r in rows)
    deltas = [r[5] for r in rows]
    mean_delta = adapt_e / base_e - 1
    p95 = quantile(deltas, .95)
    within = sum(d <= .01 + 1e-12 for d in deltas) / len(deltas)
    mx = max(deltas)
    cv = cvar_upper(deltas, .05)
    comp_red = 1 - adapt_c / base_c

    gates = {
        "mean_degradation_le_0_5pct": mean_delta <= .005 + 1e-12,
        "p95_degradation_le_1pct": p95 <= .01 + 1e-12,
        "within_1pct_world_rate_ge_97pct": within >= .97 - 1e-12,
        "max_world_degradation_le_10pct": mx <= .10 + 1e-12,
        "cvar95_degradation_le_3pct": cv <= .03 + 1e-12,
        "compute_reduction_positive": comp_red > 0,
    }
    result = {
        "experiment": "sequential-rollout-racing-v3-sealed-adversarial-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "policy": {"min_rounds": 7, "z": .75, "min_absolute_gap": 0.0, "max_rounds": 8},
        "families": list(FAMILIES),
        "worlds_evaluated": len(rows),
        "fixed_k8": {"mean_environment_cost": round(base_e, 6), "mean_rollout_samples": round(base_c, 3)},
        "adaptive": {"mean_environment_cost": round(adapt_e, 6), "mean_rollout_samples": round(adapt_c, 3)},
        "mean_environment_change_pct": round(100 * mean_delta, 3),
        "p95_world_environment_change_pct": round(100 * p95, 3),
        "within_1pct_world_rate_pct": round(100 * within, 3),
        "max_world_environment_change_pct": round(100 * mx, 3),
        "cvar95_world_environment_change_pct": round(100 * cv, 3),
        "rollout_compute_reduction_pct": round(100 * comp_red, 3),
        "by_family": {
            fam: {
                "n": len(v),
                "mean_environment_change_pct": round(100 * (statistics.fmean(r[3] for r in v) / statistics.fmean(r[1] for r in v) - 1), 3),
                "p95_world_change_pct": round(100 * quantile([r[5] for r in v], .95), 3),
                "max_world_change_pct": round(100 * max(r[5] for r in v), 3),
                "compute_reduction_pct": round(100 * (1 - statistics.fmean(r[4] for r in v) / statistics.fmean(r[2] for r in v)), 3),
            }
            for fam, v in sorted(by.items())
        },
        "sealed_gate": gates,
        "passed_predeclared_all_gate": all(gates.values()),
        "claim_boundary": "Frozen empirical racing policy evaluated on post-freeze synthetic adversarial/OOD worlds. Not a formal confidence guarantee, end-to-end LLM quality result, or wall-clock benchmark.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
