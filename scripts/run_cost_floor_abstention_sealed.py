#!/usr/bin/env python3
"""Post-freeze sealed abstention test for cost-floor pruning.

The first cost-floor OOD suite preserved the exact optimum in all worlds, but
its intended no-bound families accidentally admitted a one-step complete random
probe in 3.33% of cases. This test repairs only the *test generator*: every
initial action is constructed so that no single observation can resolve the XOR
decision. The frozen pruning algorithm is unchanged.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import json
import math
import random
import statistics

from run_context_action_dominance_bench import World, dominance_prune, exact_dp, useful_actions
from run_cost_floor_pruning_bench import dynamic_combined_prune, exact_dp_with_pruner, one_step_solve_cost

ALGORITHM_REF = "a1ecbf10a1240390c9ecca9c85a11fb043173d1c"
FREEZE_COMMIT = "149f591e29c10d0376e373d446bf2ab075a681a9"
SEALED_SEED = 104_880_233
WORLDS = 180


def normalize(xs):
    z = sum(xs)
    return tuple(x / z for x in xs)


def make_world(rng: random.Random) -> World:
    # All 8 bit patterns. Decision is XOR(bit0, bit1), which cannot be resolved
    # by bit0, bit1 or bit2 alone. Actions below are duplicates/coarsenings of
    # those single bits only; therefore no one-step complete plan exists.
    n = 8
    decisions = tuple((((i >> 0) & 1) ^ ((i >> 1) & 1)) for i in range(n))
    priors = normalize([rng.uniform(0.05, 2.0) for _ in range(n)])
    bit0 = tuple((i >> 0) & 1 for i in range(n))
    bit1 = tuple((i >> 1) & 1 for i in range(n))
    bit2 = tuple((i >> 2) & 1 for i in range(n))
    actions = [
        {"cost": rng.uniform(0.3, 1.2), "outcomes": bit0},
        {"cost": rng.uniform(0.3, 1.2), "outcomes": bit1},
        {"cost": rng.uniform(0.3, 1.2), "outcomes": bit2},
        # More expensive duplicates exercise structural pruning but cannot create
        # a direct upper bound.
        {"cost": rng.uniform(1.3, 3.0), "outcomes": bit0},
        {"cost": rng.uniform(1.3, 3.0), "outcomes": bit1},
        {"cost": rng.uniform(1.3, 3.0), "outcomes": bit2},
    ]
    return World(priors, decisions, actions, "guaranteed_no_initial_upper_bound")


def main():
    rng = random.Random(SEALED_SEED)
    exact_ok = 0
    abstain_ok = 0
    same_initial_frontier = 0
    structural_reductions = []
    combined_reductions = []

    for _ in range(WORLDS):
        world = make_world(rng)
        initial = tuple(range(world.n))
        opt = exact_dp(world)(initial)
        upper, _incumbent = one_step_solve_cost(world, initial)
        if not math.isfinite(upper):
            abstain_ok += 1
        useful = useful_actions(world, initial)
        structural, _ = dominance_prune(world, initial)
        combined, _dom, bounded, _upper = dynamic_combined_prune(world, initial)
        if not bounded and combined == structural:
            same_initial_frontier += 1
        structural_reductions.append(1 - len(structural) / len(useful))
        combined_reductions.append(1 - len(combined) / len(useful))

        pruned = exact_dp_with_pruner(world, lambda w, s: dynamic_combined_prune(w, s)[0])(initial)
        if abs(pruned - opt) <= 1e-9:
            exact_ok += 1

    result = {
        "experiment": "cost-floor-pruning-guaranteed-abstention-sealed-v0.1",
        "status": "sealed_after_freeze_test_generator_repair",
        "algorithm_ref": ALGORITHM_REF,
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "worlds": WORLDS,
        "no_initial_complete_plan_rate_pct": round(100 * abstain_ok / WORLDS, 3),
        "cost_floor_initial_abstention_rate_pct": round(100 * same_initial_frontier / WORLDS, 3),
        "exact_optimal_preservation_rate_pct": round(100 * exact_ok / WORLDS, 3),
        "structural_candidate_reduction_pct": round(100 * statistics.fmean(structural_reductions), 3),
        "combined_initial_candidate_reduction_pct": round(100 * statistics.fmean(combined_reductions), 3),
        "sealed_gate": {
            "no_initial_bound_in_all_worlds": abstain_ok == WORLDS,
            "cost_floor_abstains_initially_in_all_worlds": same_initial_frontier == WORLDS,
            "exact_optimum_preserved_all_worlds": exact_ok == WORLDS,
        },
        "note": "This follow-up exists because the first OOD generator's random probes accidentally created a one-step solution in 3.33% of intended no-bound cases. The pruning algorithm was not modified; only the generator was made constructive rather than random for the abstention property.",
        "claim_boundary": "Synthetic exact abstention test. It verifies the frozen cost-floor layer does not fabricate an upper bound when none exists initially; it is not end-to-end agent quality evidence.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
