#!/usr/bin/env python3
"""Sealed OOD evaluation for the frozen action-agreement adaptive-compute policy.

The agreement policy was frozen before the world families and seed in this file
were introduced. Both conditions use the same structural-dominance pruning and
same stochastic model; only the compute-allocation policy differs.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict

from discover_agreement_adaptive_rollout import AgreementPolicy, evaluate
from run_context_action_dominance_bench import World

FREEZE_COMMIT = "778869fec07a52d4c6af873030defba4a60cc186"
SEALED_SEED = 31_770_413
WORLDS_PER_FAMILY = 60
FROZEN_POLICY = AgreementPolicy(
    pilot_rounds=2,
    min_agreement=0.75,
    require_feature_margin=1.0,
)
FAMILIES = (
    "adversarial_vote_split",
    "rare_branch_chain",
    "cost_aliasing",
    "multi_step_decoy",
    "low_entropy_decisive",
    "heteroskedastic_structure",
)


def normalize(xs):
    z = sum(xs)
    return [x / z for x in xs]


def random_partition(rng: random.Random, n: int, k: int):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def add(actions, cost, outcomes):
    actions.append({"cost": float(cost), "outcomes": tuple(outcomes)})


def make_world(seed: int, family: str) -> World:
    rng = random.Random(seed)
    n = rng.randint(6, 9)
    dcount = rng.choice([2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d

    if family == "low_entropy_decisive":
        raw = [rng.uniform(0.02, 0.12) for _ in range(n)]
        raw[rng.randrange(n)] = rng.uniform(4.0, 8.0)
    elif family == "rare_branch_chain":
        raw = [rng.uniform(0.4, 1.4) for _ in range(n)]
        raw[rng.randrange(n)] *= rng.uniform(0.02, 0.08)
    else:
        raw = [rng.gammavariate(rng.uniform(0.45, 2.3), 1.0) for _ in range(n)]
    priors = normalize(raw)
    actions = []

    if family == "adversarial_vote_split":
        # Several near-equivalent candidates with distinct downstream branches.
        # Pilot races should often disagree here, forcing full compute.
        base = rng.uniform(1.0, 1.8)
        for _ in range(rng.randint(11, 15)):
            add(actions, base * rng.uniform(0.93, 1.07), random_partition(rng, n, rng.choice([2, 3, 4])))

    elif family == "rare_branch_chain":
        for bit in range(4):
            outcomes = tuple((i >> bit) & 1 for i in range(n))
            if len(set(outcomes)) > 1:
                add(actions, rng.uniform(0.35, 0.95), outcomes)
        rare = min(range(n), key=lambda i: priors[i])
        rare_probe = [0] * n
        rare_probe[rare] = 1
        add(actions, rng.uniform(0.45, 1.0), rare_probe)
        for _ in range(5):
            add(actions, rng.uniform(0.7, 1.6), random_partition(rng, n, 2))

    elif family == "cost_aliasing":
        # Similar observation structures at nearly identical costs test whether
        # pilot agreement is robust to economically ambiguous candidates.
        bases = []
        for _ in range(6):
            outcomes = random_partition(rng, n, rng.choice([2, 3]))
            cost = rng.uniform(0.8, 1.8)
            add(actions, cost, outcomes)
            bases.append((cost, outcomes))
        for cost, outcomes in bases[:4]:
            variant = list(outcomes)
            if rng.random() < 0.5:
                rng.shuffle(variant)
            add(actions, cost * rng.uniform(0.97, 1.08), variant)

    elif family == "multi_step_decoy":
        # Cheap high-information partitions are intentionally weak with respect
        # to final decisions; several decision-aligned binary probes compete.
        for _ in range(7):
            ordering = list(range(n))
            rng.shuffle(ordering)
            k = rng.choice([3, 4])
            add(actions, rng.uniform(0.45, 1.15), tuple(x % k for x in ordering))
        for d in range(dcount):
            aligned = tuple(1 if x == d else 0 for x in decisions)
            if len(set(aligned)) > 1:
                add(actions, rng.uniform(0.8, 1.7), aligned)

    elif family == "low_entropy_decisive":
        # Most probability mass is already concentrated, but resolving the tail
        # can still change the final decision policy.
        for _ in range(8):
            add(actions, rng.uniform(0.4, 1.5), random_partition(rng, n, rng.choice([2, 3])))
        for d in range(dcount):
            aligned = tuple(1 if x == d else 0 for x in decisions)
            if len(set(aligned)) > 1:
                add(actions, rng.uniform(0.9, 2.2), aligned)

    elif family == "heteroskedastic_structure":
        # Mix cheap/coarse, expensive/fine and redundant refinements so the
        # rollout outcome distributions differ substantially by candidate.
        for _ in range(5):
            add(actions, rng.uniform(0.25, 0.8), random_partition(rng, n, 2))
        fine = []
        for _ in range(5):
            outcomes = random_partition(rng, n, rng.choice([3, 4, 5]))
            cost = rng.uniform(1.3, 4.0)
            add(actions, cost, outcomes)
            fine.append((cost, outcomes))
        for cost, outcomes in fine[:3]:
            add(actions, cost * rng.uniform(1.15, 2.0), outcomes)

    add(actions, rng.uniform(1.8, 5.8), tuple(decisions))
    return World(priors, decisions, actions, family)


def quantile(values, q):
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def main():
    rng = random.Random(SEALED_SEED)
    rows = []
    by_family = defaultdict(list)
    for family in FAMILIES:
        for _ in range(WORLDS_PER_FAMILY):
            world = make_world(rng.randrange(1_000_000_000), family)
            idx = len(rows)
            eval_seed = SEALED_SEED + idx * 83 + 31
            fixed_env, fixed_compute = evaluate(world, eval_seed, None)
            adaptive_env, adaptive_compute = evaluate(world, eval_seed, FROZEN_POLICY)
            if not all(math.isfinite(x) for x in (fixed_env, fixed_compute, adaptive_env, adaptive_compute)):
                continue
            delta = adaptive_env / fixed_env - 1.0
            row = (family, fixed_env, adaptive_env, fixed_compute, adaptive_compute, delta)
            rows.append(row)
            by_family[family].append(row)

    fixed_e = statistics.fmean(r[1] for r in rows)
    adapt_e = statistics.fmean(r[2] for r in rows)
    fixed_c = statistics.fmean(r[3] for r in rows)
    adapt_c = statistics.fmean(r[4] for r in rows)
    deltas = [r[5] for r in rows]

    result = {
        "experiment": "agreement-adaptive-rollout-sealed-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "families": list(FAMILIES),
        "worlds_evaluated": len(rows),
        "fixed_k8": {
            "mean_environment_cost": round(fixed_e, 6),
            "mean_rollout_samples": round(fixed_c, 3),
        },
        "agreement_adaptive": {
            "mean_environment_cost": round(adapt_e, 6),
            "mean_rollout_samples": round(adapt_c, 3),
        },
        "mean_environment_cost_change_pct": round(100 * (adapt_e / fixed_e - 1.0), 3),
        "mean_rollout_compute_reduction_pct": round(100 * (1.0 - adapt_c / fixed_c), 3),
        "world_delta_distribution_pct": {
            "median": round(100 * statistics.median(deltas), 3),
            "p90": round(100 * quantile(deltas, 0.90), 3),
            "p95": round(100 * quantile(deltas, 0.95), 3),
            "max": round(100 * max(deltas), 3),
        },
        "no_worse_world_rate_pct": round(100 * sum(d <= 1e-12 for d in deltas) / len(deltas), 3),
        "within_1pct_world_rate_pct": round(100 * sum(d <= 0.01 + 1e-12 for d in deltas) / len(deltas), 3),
        "by_family": {
            fam: {
                "n": len(vals),
                "mean_environment_change_pct": round(100 * (statistics.fmean(v[2] for v in vals) / statistics.fmean(v[1] for v in vals) - 1.0), 3),
                "mean_compute_reduction_pct": round(100 * (1.0 - statistics.fmean(v[4] for v in vals) / statistics.fmean(v[3] for v in vals)), 3),
                "within_1pct_world_rate_pct": round(100 * sum(v[5] <= 0.01 + 1e-12 for v in vals) / len(vals), 3),
            }
            for fam, vals in sorted(by_family.items())
        },
        "sealed_gate": {
            "mean_environment_degradation_le_1pct": (adapt_e / fixed_e - 1.0) <= 0.01 + 1e-12,
            "compute_reduction_positive": adapt_c < fixed_c,
        },
        "claim_boundary": "Frozen action-agreement controller evaluated on new post-freeze synthetic OOD families and seed. This remains synthetic controller evidence, not an independent external benchmark or real-agent answer-quality result.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
