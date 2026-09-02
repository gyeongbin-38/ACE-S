#!/usr/bin/env python3
"""Sealed OOD test for frozen cost-floor + structural dominance pruning.

The pruning rule was frozen before the families and seed in this file were
introduced. The suite deliberately includes worlds with no one-step complete
plan, where cost-floor pruning must abstain and exactness must still hold.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict

from run_context_action_dominance_bench import World, dominance_prune, exact_dp, useful_actions
from run_cost_floor_pruning_bench import dynamic_combined_prune, exact_dp_with_pruner

FREEZE_COMMIT = "149f591e29c10d0376e373d446bf2ab075a681a9"
ALGORITHM_REF = "a1ecbf10a1240390c9ecca9c85a11fb043173d1c"
SEALED_SEED = 93_771_409
WORLDS_PER_FAMILY = 60
FAMILIES = (
    "no_direct_upper",
    "late_upper_emerges",
    "cheap_complete_plan",
    "expensive_complete_plan",
    "incomparable_high_cost",
    "deep_binary_resolution",
)


def normalize(xs):
    z = sum(xs)
    return [x / z for x in xs]


def add(actions, cost, outcomes):
    actions.append({"cost": float(cost), "outcomes": tuple(outcomes)})


def random_partition(rng, n, k):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def make_xor_world(rng: random.Random, family: str) -> World:
    n = 8
    decisions = tuple((((i >> 0) & 1) ^ ((i >> 1) & 1)) for i in range(n))
    priors = normalize([rng.uniform(0.2, 1.8) for _ in range(n)])
    actions = []
    bit0 = tuple((i >> 0) & 1 for i in range(n))
    bit1 = tuple((i >> 1) & 1 for i in range(n))
    bit2 = tuple((i >> 2) & 1 for i in range(n))
    add(actions, rng.uniform(0.4, 1.1), bit0)
    add(actions, rng.uniform(0.4, 1.1), bit1)
    add(actions, rng.uniform(0.4, 1.1), bit2)
    for _ in range(4):
        add(actions, rng.uniform(0.7, 2.5), random_partition(rng, n, 2))

    if family == "late_upper_emerges":
        # No initial one-step solution. After a bit observation, another action
        # can become decision-sufficient on the narrowed state.
        add(actions, rng.uniform(1.0, 2.4), tuple((i >> 0) & 1 for i in range(n)))
    elif family == "deep_binary_resolution":
        # Keep only multi-step resolving structure; no direct decision action.
        for _ in range(3):
            add(actions, rng.uniform(1.0, 3.0), random_partition(rng, n, 2))
    return World(priors, decisions, actions, family)


def make_direct_world(rng: random.Random, family: str) -> World:
    n = rng.randint(6, 9)
    dcount = rng.choice([2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d
    priors = normalize([rng.gammavariate(rng.uniform(0.5, 2.0), 1.0) for _ in range(n)])
    actions = []
    for _ in range(rng.randint(7, 11)):
        if family == "incomparable_high_cost":
            cost = math.exp(rng.uniform(math.log(1.0), math.log(12.0)))
        else:
            cost = math.exp(rng.uniform(math.log(0.35), math.log(7.0)))
        add(actions, cost, random_partition(rng, n, rng.choice([2, 3, 4])))

    if family == "cheap_complete_plan":
        direct_cost = rng.uniform(0.45, 1.2)
    elif family == "expensive_complete_plan":
        direct_cost = rng.uniform(5.0, 10.0)
    else:
        direct_cost = rng.uniform(1.5, 4.5)
    add(actions, direct_cost, tuple(decisions))

    if family == "incomparable_high_cost":
        # Add several costly partitions that do not necessarily refine the direct
        # plan but can be eliminated by its feasible cost upper bound.
        for _ in range(6):
            add(actions, direct_cost * rng.uniform(1.05, 3.0), random_partition(rng, n, rng.choice([2, 3, 4])))
    return World(priors, tuple(decisions), actions, family)


def make_world(seed: int, family: str) -> World:
    rng = random.Random(seed)
    if family in {"no_direct_upper", "late_upper_emerges", "deep_binary_resolution"}:
        return make_xor_world(rng, family)
    return make_direct_world(rng, family)


def main():
    rng = random.Random(SEALED_SEED)
    checked = exact_preserved = 0
    bound_available = 0
    structural_reductions = []
    combined_reductions = []
    incremental = []
    by_family = defaultdict(lambda: {"struct": [], "combined": [], "incremental": [], "bound": [], "exact": []})

    for family in FAMILIES:
        for _ in range(WORLDS_PER_FAMILY):
            world = make_world(rng.randrange(1_000_000_000), family)
            initial = tuple(range(world.n))
            optimum = exact_dp(world)(initial)
            if not math.isfinite(optimum):
                continue
            useful = useful_actions(world, initial)
            structural, _ = dominance_prune(world, initial)
            combined, _dom, _bounded, upper = dynamic_combined_prune(world, initial)
            if math.isfinite(upper):
                bound_available += 1
            sr = 1 - len(structural) / len(useful)
            cr = 1 - len(combined) / len(useful)
            inc = 1 - len(combined) / len(structural) if structural else 0.0
            structural_reductions.append(sr)
            combined_reductions.append(cr)
            incremental.append(inc)

            pruned_dp = exact_dp_with_pruner(world, lambda w, s: dynamic_combined_prune(w, s)[0])
            pruned = pruned_dp(initial)
            ok = abs(pruned - optimum) <= 1e-9
            checked += 1
            exact_preserved += int(ok)
            row = by_family[family]
            row["struct"].append(sr)
            row["combined"].append(cr)
            row["incremental"].append(inc)
            row["bound"].append(1.0 if math.isfinite(upper) else 0.0)
            row["exact"].append(1.0 if ok else 0.0)

    result = {
        "experiment": "cost-floor-plus-dominance-pruning-sealed-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "algorithm_ref": ALGORITHM_REF,
        "sealed_seed": SEALED_SEED,
        "families": list(FAMILIES),
        "worlds_evaluated": checked,
        "initial_feasible_upper_bound_available_pct": round(100 * bound_available / checked, 3),
        "exact_optimal_preservation_rate_pct": round(100 * exact_preserved / checked, 3),
        "structural_dominance_candidate_reduction_pct": round(100 * statistics.fmean(structural_reductions), 3),
        "combined_candidate_reduction_pct": round(100 * statistics.fmean(combined_reductions), 3),
        "incremental_reduction_of_structural_frontier_pct": round(100 * statistics.fmean(incremental), 3),
        "by_family": {
            fam: {
                "n": len(v["exact"]),
                "initial_upper_bound_available_pct": round(100 * statistics.fmean(v["bound"]), 3),
                "exact_optimal_preservation_pct": round(100 * statistics.fmean(v["exact"]), 3),
                "structural_reduction_pct": round(100 * statistics.fmean(v["struct"]), 3),
                "combined_reduction_pct": round(100 * statistics.fmean(v["combined"]), 3),
                "incremental_frontier_reduction_pct": round(100 * statistics.fmean(v["incremental"]), 3),
            }
            for fam, v in sorted(by_family.items())
        },
        "sealed_gate": {
            "exact_optimum_preserved_all_worlds": exact_preserved == checked,
            "abstains_when_no_valid_initial_upper_bound": all(
                statistics.fmean(by_family[f]["bound"]) == 0.0
                for f in ("no_direct_upper", "late_upper_emerges", "deep_binary_resolution")
            ),
        },
        "claim_boundary": "Frozen exact pruning rule on post-freeze synthetic OOD families. Cost-floor pruning only applies when a real complete-plan upper bound exists; no-bound families test abstention. This is not end-to-end LLM answer-quality evidence.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
