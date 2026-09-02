#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
import statistics

import discover_retention_scheduler as ret
import run_second_sealed_scheduler_test as sealed

BASE_POLICY = ret.Policy(
    benefit_exp=1.0,
    cost_exp=0.75,
    exact_weight=1.5,
    abstract_risk_weight=1.5,
    discount=1.0,
    threshold=1.2,
)
SIGMAS = [0.0, 0.5, 1.0]
NOISE_SEEDS = [7_331_019, 7_331_037]
DEV_SEED = 7_331_001


def summarize(values: list[float]) -> dict:
    v = sorted(values)
    return {
        "mean": round(statistics.fmean(v), 5),
        "median": round(statistics.median(v), 5),
        "p90": round(v[int(0.90 * (len(v) - 1))], 5),
        "p95": round(v[int(0.95 * (len(v) - 1))], 5),
        "within_05pct": round(100 * sum(x <= 1.05 + 1e-12 for x in v) / len(v), 2),
        "within_10pct": round(100 * sum(x <= 1.10 + 1e-12 for x in v) / len(v), 2),
        "within_25pct": round(100 * sum(x <= 1.25 + 1e-12 for x in v) / len(v), 2),
    }


def feasible_modes(available: str) -> tuple[str, ...]:
    if available == ret.RAW:
        return (ret.DROP, ret.ABSTRACT, ret.RAW)
    if available == ret.ABSTRACT:
        return (ret.DROP, ret.ABSTRACT)
    return (ret.DROP,)


def transition_cost(item: ret.Item, available: str, chosen: str) -> float:
    if available == ret.RAW and chosen == ret.ABSTRACT:
        return item.compact_cost
    return 0.0


def step_expected_cost(item: ret.Item, t: int, mode: str, continuation) -> float:
    """True expected one-step cost plus continuation after the observation.

    continuation(next_t, available_after_observation) is evaluated after need/no-need outcome.
    Exact needs or abstraction failures reacquire RAW before continuation.
    """
    hold = item.raw_hold if mode == ret.RAW else item.abstract_hold if mode == ret.ABSTRACT else 0.0
    pn = item.p_need[t]
    pe = item.p_exact[t]
    next_t = t + 1

    if next_t >= len(item.p_need):
        cont_none = lambda _available: 0.0
    else:
        cont_none = lambda available: continuation(next_t, available)

    no_need = cont_none(mode)
    if mode == ret.RAW:
        need = cont_none(ret.RAW)
    elif mode == ret.DROP:
        need = item.reacquire_cost + cont_none(ret.RAW)
    else:
        exact = item.reacquire_cost + cont_none(ret.RAW)
        semantic_success = cont_none(ret.ABSTRACT)
        semantic_fail = item.reacquire_cost + cont_none(ret.RAW)
        semantic = (1.0 - item.abstract_failure) * semantic_success + item.abstract_failure * semantic_fail
        need = pe * exact + (1.0 - pe) * semantic
    return hold + (1.0 - pn) * no_need + pn * need


def retention_base_and_rollout(item: ret.Item, iid: int, sigma: float, nseed: int):
    """Compare frozen heuristic vs one-step policy rollout from initial RAW availability."""

    @functools.lru_cache(maxsize=None)
    def base_from_available(t: int, available: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        chosen = ret.policy_choice(item, t, available, BASE_POLICY, sigma, nseed, iid)
        trans = transition_cost(item, available, chosen)
        return trans + step_expected_cost(item, t, chosen, base_from_available)

    @functools.lru_cache(maxsize=None)
    def rollout_from_available(t: int, available: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        ranked = []
        for chosen in feasible_modes(available):
            trans = transition_cost(item, available, chosen)
            # Policy rollout: score the current lifecycle action by true immediate cost
            # plus the frozen base policy's expected cost-to-go after the next observation.
            estimate = trans + step_expected_cost(item, t, chosen, base_from_available)
            ranked.append((estimate, trans, {ret.DROP: 0, ret.ABSTRACT: 1, ret.RAW: 2}[chosen], chosen))
        _estimate, _trans, _rank, chosen = min(ranked)
        return transition_cost(item, available, chosen) + step_expected_cost(item, t, chosen, rollout_from_available)

    return base_from_available(0, ret.RAW), rollout_from_available(0, ret.RAW)


def main() -> None:
    # Mix the original development distribution with the later difficult OOD families,
    # but use a fresh development seed. This remains development-only before any freeze.
    regular = ret.make_items(DEV_SEED, 160)
    ood = sealed.make_retention_worlds(DEV_SEED + 101, 30)
    items = [(iid, item, opt, item.family) for iid, item, opt in regular]
    offset = len(items)
    items.extend((offset + iid, item, opt, family) for iid, item, opt, family in ood)

    base_vals: list[float] = []
    rollout_vals: list[float] = []
    by_family: dict[str, dict[str, list[float]]] = {}
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                base, rollout = retention_base_and_rollout(item, iid, sigma, nseed)
                base_vals.append(base / opt)
                rollout_vals.append(rollout / opt)
                row = by_family.setdefault(family, {"base": [], "rollout": []})
                row["base"].append(base / opt)
                row["rollout"].append(rollout / opt)

    result = {
        "experiment": "retention-policy-rollout-development-v0.1",
        "status": "development_only_before_freeze",
        "items": len(items),
        "evaluations": len(rollout_vals),
        "sigmas": SIGMAS,
        "base_frozen_retention_policy": summarize(base_vals),
        "rollout_retention_policy": summarize(rollout_vals),
        "rollout_beats_or_ties_base_rate": round(100 * sum(r <= b + 1e-12 for r, b in zip(rollout_vals, base_vals)) / len(base_vals), 2),
        "mean_cost_reduction_vs_base_pct": round(100 * (1 - statistics.fmean(rollout_vals) / statistics.fmean(base_vals)), 2),
        "by_family": {k: {name: summarize(vals) for name, vals in v.items()} for k, v in sorted(by_family.items())},
        "algorithm": "One-step receding-horizon policy rollout over lifecycle actions RAW/ABSTRACT/DROP. Each candidate is scored by immediate measured transition/residency/reacquisition expectation plus the frozen base retention policy's expected remaining cost; execute one lifecycle choice and replan after the need/exactness outcome.",
        "guardrail": "Development only. No sealed retention-rollout seed or post-freeze result is present. Freeze the algorithm before introducing unseen lifecycle worlds.",
        "caveat": "Synthetic lifecycle mechanics. The rollout evaluator uses true need/exactness probabilities for current expected cost and exact base-policy cost-to-go; a real agent must estimate these probabilities."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
