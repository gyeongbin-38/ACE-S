#!/usr/bin/env python3
"""Development benchmark for deterministic cost-floor candidate pruning.

If the controller already knows a complete one-step context plan with total
cost U, then any alternative first action whose *immediate measured cost* is
>= U cannot produce a cheaper complete plan because all future costs are
non-negative. Such an action can be removed before any rollout, even when its
observation partition is incomparable to the incumbent plan.

This rule composes with structural dominance pruning. It is exact under the
benchmark's non-negative measured-cost model. Synthetic controller mechanics;
not end-to-end LLM evidence.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from collections import defaultdict

from run_context_action_dominance_bench import (
    World,
    dominance_prune,
    exact_dp,
    gen_world,
    partitions,
    useful_actions,
)

DEV_SEED = 82_410_773
WORLDS = 360
FAMILIES = ("mixed", "light_redundancy", "heavy_redundancy", "costly_coarse")


def one_step_solve_cost(world: World, subset):
    best = math.inf
    best_action = None
    for a in useful_actions(world, subset):
        parts = list(partitions(world, subset, a))
        if parts and all(world.solved(state) for _p, state in parts):
            cost = world.actions[a]["cost"]
            if cost < best:
                best = cost
                best_action = a
    return best, best_action


def cost_floor_prune(world: World, subset, candidates):
    upper, incumbent = one_step_solve_cost(world, subset)
    if not math.isfinite(upper):
        return list(candidates), {}, upper
    keep = []
    removed = {}
    for a in candidates:
        if a == incumbent:
            keep.append(a)
            continue
        cost = world.actions[a]["cost"]
        if cost >= upper - 1e-12:
            removed[a] = incumbent
        else:
            keep.append(a)
    return keep, removed, upper


def dynamic_combined_prune(world: World, subset):
    structural, dominated = dominance_prune(world, subset)
    kept, bounded, upper = cost_floor_prune(world, subset, structural)
    return kept, dominated, bounded, upper


def exact_dp_with_pruner(world: World, pruner):
    import functools

    @functools.lru_cache(None)
    def dp(subset):
        if world.solved(subset):
            return 0.0
        candidates = pruner(world, subset)
        best = math.inf
        for a in candidates:
            parts = list(partitions(world, subset, a))
            p_self = sum(p for p, state in parts if state == subset)
            if p_self >= 1.0 - 1e-12:
                continue
            rest = sum(p * dp(state) for p, state in parts if state != subset)
            q = (world.actions[a]["cost"] + rest) / (1.0 - p_self)
            best = min(best, q)
        return best

    return dp


def main():
    rng = random.Random(DEV_SEED)
    candidate_reduction_struct = []
    candidate_reduction_combined = []
    cost_floor_incremental = []
    exact_preserved = 0
    checked = 0
    upper_available = 0
    by_family = defaultdict(lambda: {"struct": [], "combined": [], "incremental": [], "upper": []})

    for i in range(WORLDS):
        family = FAMILIES[i % len(FAMILIES)]
        world = gen_world(rng.randrange(1_000_000_000), family)
        initial = tuple(range(world.n))
        optimal = exact_dp(world)(initial)
        if not math.isfinite(optimal):
            continue
        useful = useful_actions(world, initial)
        structural, _ = dominance_prune(world, initial)
        combined, _dom, _bound, upper = dynamic_combined_prune(world, initial)
        if math.isfinite(upper):
            upper_available += 1
        sr = 1.0 - len(structural) / len(useful)
        cr = 1.0 - len(combined) / len(useful)
        inc = 1.0 - len(combined) / len(structural) if structural else 0.0
        candidate_reduction_struct.append(sr)
        candidate_reduction_combined.append(cr)
        cost_floor_incremental.append(inc)
        by_family[family]["struct"].append(sr)
        by_family[family]["combined"].append(cr)
        by_family[family]["incremental"].append(inc)
        by_family[family]["upper"].append(1.0 if math.isfinite(upper) else 0.0)

        combined_dp = exact_dp_with_pruner(world, lambda w, s: dynamic_combined_prune(w, s)[0])
        pruned_opt = combined_dp(initial)
        checked += 1
        if abs(pruned_opt - optimal) <= 1e-9:
            exact_preserved += 1

    result = {
        "experiment": "cost-floor-plus-dominance-pruning-development-v0.1",
        "status": "development_only",
        "worlds_evaluated": checked,
        "one_step_feasible_upper_bound_available_pct": round(100 * upper_available / checked, 3),
        "exact_optimal_preservation_rate_pct": round(100 * exact_preserved / checked, 3),
        "structural_dominance_candidate_reduction_pct": round(100 * statistics.fmean(candidate_reduction_struct), 3),
        "combined_candidate_reduction_pct": round(100 * statistics.fmean(candidate_reduction_combined), 3),
        "incremental_reduction_of_structural_frontier_pct": round(100 * statistics.fmean(cost_floor_incremental), 3),
        "by_family": {
            fam: {
                "structural_reduction_pct": round(100 * statistics.fmean(vals["struct"]), 3),
                "combined_reduction_pct": round(100 * statistics.fmean(vals["combined"]), 3),
                "incremental_frontier_reduction_pct": round(100 * statistics.fmean(vals["incremental"]), 3),
                "upper_bound_available_pct": round(100 * statistics.fmean(vals["upper"]), 3),
            }
            for fam, vals in sorted(by_family.items())
        },
        "rule": "Given a known complete feasible plan with total cost U and non-negative future costs, remove any alternative first action a with measured immediate cost c(a) >= U. Compose after structural dominance pruning.",
        "claim_boundary": "Exact only when U is a genuinely feasible complete-plan upper bound and all modeled future costs are non-negative and comparable. This benchmark obtains U from a one-step action whose every observation cell is already decision-sufficient. Real runtimes must not use an estimated/uncertain U as an exact pruning bound.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
