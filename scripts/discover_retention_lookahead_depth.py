#!/usr/bin/env python3
"""Development experiment for deeper lifecycle lookahead.

The current frozen retention rollout uses one-step policy improvement over the
frozen heuristic. Its main sealed weakness is long-idle -> late-revival state.
This benchmark compares depth-1, depth-2 and depth-3 receding-horizon policy
improvement on new development-only revival-heavy lifecycle families.

Synthetic expected lifecycle economics only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics

import discover_retention_scheduler as ret
from run_retention_rollout_bench import (
    BASE_POLICY,
    feasible_modes,
    step_expected_cost,
    transition_cost,
)

DEV_SEED = 18_203_117
NOISE_SEEDS = [18_203_129, 18_203_147]
SIGMAS = [0.0, 0.5, 1.0]
ITEMS_PER_FAMILY = 45
DEPTHS = (1, 2, 3)
FAMILIES = (
    "late_single_revival",
    "double_revival",
    "idle_then_exact_burst",
    "long_quiet_periodic_return",
    "false_revival_risk",
)


def clamp(x, lo=0.01, hi=0.98):
    return min(hi, max(lo, x))


def make_item(rng: random.Random, family: str) -> ret.Item:
    horizon = rng.randint(10, 16)
    p_need = [rng.uniform(0.01, 0.09) for _ in range(horizon)]
    p_exact = [rng.uniform(0.12, 0.55) for _ in range(horizon)]

    if family == "late_single_revival":
        start = rng.randint(horizon - 5, horizon - 2)
        for t in range(start, horizon):
            p_need[t] = rng.uniform(0.62, 0.94)

    elif family == "double_revival":
        a = rng.randint(2, max(3, horizon // 3))
        b = rng.randint(max(a + 3, horizon // 2), horizon - 2)
        for t in range(max(0, a - 1), min(horizon, a + 2)):
            p_need[t] = rng.uniform(0.5, 0.88)
        for t in range(b, horizon):
            p_need[t] = rng.uniform(0.55, 0.92)

    elif family == "idle_then_exact_burst":
        start = rng.randint(horizon - 5, horizon - 2)
        for t in range(start, horizon):
            p_need[t] = rng.uniform(0.45, 0.82)
            p_exact[t] = rng.uniform(0.82, 0.98)
        for t in range(start):
            p_exact[t] = rng.uniform(0.03, 0.18)

    elif family == "long_quiet_periodic_return":
        period = rng.choice([3, 4, 5])
        phase = rng.randrange(period)
        for t in range(horizon):
            if t >= horizon // 2 and t % period == phase:
                p_need[t] = rng.uniform(0.6, 0.93)
            else:
                p_need[t] = rng.uniform(0.015, 0.08)

    elif family == "false_revival_risk":
        # Several modest late bumps, but no guaranteed large return. This family
        # penalizes overly conservative policies that keep RAW just in case.
        bumps = rng.sample(range(horizon // 2, horizon), k=min(3, horizon - horizon // 2))
        for t in bumps:
            p_need[t] = rng.uniform(0.18, 0.42)
        p_exact = [rng.uniform(0.05, 0.35) for _ in range(horizon)]

    reacquire = rng.uniform(3.0, 10.0)
    raw_hold = rng.uniform(0.18, 0.95)
    abstract_hold = raw_hold * rng.uniform(0.05, 0.25)
    compact_cost = rng.uniform(0.1, 1.3)
    abstract_failure = rng.uniform(0.03, 0.3)

    if family in {"late_single_revival", "double_revival", "idle_then_exact_burst"}:
        reacquire *= rng.uniform(1.2, 2.3)
    if family == "false_revival_risk":
        raw_hold *= rng.uniform(1.1, 1.8)

    return ret.Item(
        tuple(clamp(x) for x in p_need),
        tuple(clamp(x) for x in p_exact),
        raw_hold,
        abstract_hold,
        reacquire,
        compact_cost,
        clamp(abstract_failure, 0.01, 0.75),
        family,
    )


def rollout_cost(item: ret.Item, iid: int, sigma: float, nseed: int, depth: int):
    """Execute a depth-d receding-horizon policy; fall back to base after d steps in scoring."""

    @functools.lru_cache(maxsize=None)
    def base_from_available(t: int, available: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        chosen = ret.policy_choice(item, t, available, BASE_POLICY, sigma, nseed, iid)
        return transition_cost(item, available, chosen) + step_expected_cost(item, t, chosen, base_from_available)

    @functools.lru_cache(maxsize=None)
    def lookahead_value(t: int, available: str, remaining_depth: int) -> float:
        if t >= len(item.p_need):
            return 0.0
        if remaining_depth <= 0:
            return base_from_available(t, available)
        best = math.inf
        for chosen in feasible_modes(available):
            q = transition_cost(item, available, chosen)
            q += step_expected_cost(
                item,
                t,
                chosen,
                lambda nt, nav: lookahead_value(nt, nav, remaining_depth - 1),
            )
            best = min(best, q)
        return best

    @functools.lru_cache(maxsize=None)
    def execute(t: int, available: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        ranked = []
        for chosen in feasible_modes(available):
            q = transition_cost(item, available, chosen)
            q += step_expected_cost(
                item,
                t,
                chosen,
                lambda nt, nav: lookahead_value(nt, nav, depth - 1),
            )
            ranked.append((q, {ret.DROP: 0, ret.ABSTRACT: 1, ret.RAW: 2}[chosen], chosen))
        _q, _rank, selected = min(ranked)
        return transition_cost(item, available, selected) + step_expected_cost(item, t, selected, execute)

    return execute(0, ret.RAW)


def summarize(vals):
    xs = sorted(vals)
    return {
        "mean": round(statistics.fmean(xs), 5),
        "median": round(statistics.median(xs), 5),
        "p90": round(xs[int(0.90 * (len(xs)-1))], 5),
        "p95": round(xs[int(0.95 * (len(xs)-1))], 5),
        "within_05pct": round(100 * sum(x <= 1.05 + 1e-12 for x in xs) / len(xs), 2),
        "within_10pct": round(100 * sum(x <= 1.10 + 1e-12 for x in xs) / len(xs), 2),
    }


def main():
    rng = random.Random(DEV_SEED)
    items = []
    iid = 0
    for family in FAMILIES:
        for _ in range(ITEMS_PER_FAMILY):
            item = make_item(rng, family)
            opt = ret.optimal_cost(item)
            items.append((iid, item, opt, family))
            iid += 1

    all_vals = {depth: [] for depth in DEPTHS}
    by_family = {family: {depth: [] for depth in DEPTHS} for family in FAMILIES}
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                for depth in DEPTHS:
                    ratio = rollout_cost(item, iid, sigma, nseed, depth) / opt
                    all_vals[depth].append(ratio)
                    by_family[family][depth].append(ratio)

    d1 = statistics.fmean(all_vals[1])
    result = {
        "experiment": "retention-lookahead-depth-development-v0.1",
        "status": "development_only",
        "items": len(items),
        "evaluations_per_depth": len(all_vals[1]),
        "families": list(FAMILIES),
        "depth_results": {f"depth_{d}": summarize(all_vals[d]) for d in DEPTHS},
        "mean_cost_reduction_vs_depth1_pct": {
            f"depth_{d}": round(100 * (1 - statistics.fmean(all_vals[d]) / d1), 3)
            for d in DEPTHS if d != 1
        },
        "by_family": {
            family: {f"depth_{d}": summarize(vals[d]) for d in DEPTHS}
            for family, vals in by_family.items()
        },
        "guardrail": "Development only. Do not tune on the prior sealed retention suite and then describe that suite as holdout. Freeze any chosen depth/trigger rule before introducing another post-freeze lifecycle family/seed.",
        "claim_boundary": "Synthetic expected lifecycle economics using true need/exactness probabilities in the evaluator. Deeper lookahead increases controller planning work; a follow-up must test a selective trigger rather than globally increasing depth if gains are localized.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
