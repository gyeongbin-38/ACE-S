#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
import math
import random
import statistics

import discover_context_acquisition_policy as acq
import discover_resolution_scheduler as res
import run_information_value_bench as info

FROZEN_ACQUISITION = acq.Policy(
    ig_exp=0.35,
    cost_exp=1.25,
    gini_weight=1.0,
    solve_weight=1.5,
    worst_weight=0.5,
    count_weight=0.5,
)
FROZEN_RESOLUTION_ZERO_SHOT = res.Policy(
    ig_exp=0.35,
    cost_exp=1.25,
    gini_weight=1.0,
    solve_weight=1.5,
    worst_weight=0.5,
    count_weight=0.5,
    span_weight=0.0,
)
SIGMAS = [0.0, 0.5, 1.0]
NOISE_SEEDS = [930_701, 930_709]


def summarize(values: list[float]) -> dict:
    v = sorted(values)
    return {
        "mean": round(statistics.fmean(v), 5),
        "median": round(statistics.median(v), 5),
        "p90": round(v[int(0.9 * (len(v) - 1))], 5),
        "within_10pct": round(100 * sum(x <= 1.10 + 1e-12 for x in v) / len(v), 2),
        "within_25pct": round(100 * sum(x <= 1.25 + 1e-12 for x in v) / len(v), 2),
    }


def make_acquisition_worlds(seed: int, per_family: int = 16):
    rng = random.Random(seed)
    worlds = []
    iid = 0
    for family in ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]:
        for _ in range(per_family):
            inst = info.make_instance(rng, family)
            worlds.append((iid, inst, info.optimal_cost(inst)))
            iid += 1
    return worlds


def acquisition_base_and_rollout(inst, iid: int, sigma: float, nseed: int):
    base_choose = acq.chooser(FROZEN_ACQUISITION, iid, sigma, nseed)
    all_h = tuple(range(len(inst.decisions)))
    all_q = tuple(range(len(inst.queries)))

    @functools.lru_cache(maxsize=None)
    def base(active: tuple[int, ...], remaining: tuple[int, ...]) -> float:
        if info.solved(inst, active):
            return 0.0
        candidates = [q for q in remaining if info.useful(inst, active, q)]
        if not candidates:
            return math.inf
        q = base_choose(inst, active, candidates)
        nr = tuple(x for x in remaining if x != q)
        return inst.queries[q].cost + sum(p * base(st, nr) for p, st in info.partitions(inst, active, q))

    @functools.lru_cache(maxsize=None)
    def rollout(active: tuple[int, ...], remaining: tuple[int, ...]) -> float:
        if info.solved(inst, active):
            return 0.0
        candidates = [q for q in remaining if info.useful(inst, active, q)]
        if not candidates:
            return math.inf
        ranked = []
        for q in candidates:
            nr = tuple(x for x in remaining if x != q)
            estimated = inst.queries[q].cost + sum(p * base(st, nr) for p, st in info.partitions(inst, active, q))
            ranked.append((estimated, inst.queries[q].cost, q))
        _estimate, _cost, q = min(ranked)
        nr = tuple(x for x in remaining if x != q)
        return inst.queries[q].cost + sum(p * rollout(st, nr) for p, st in info.partitions(inst, active, q))

    return base(all_h, all_q), rollout(all_h, all_q)


def resolution_base_and_rollout(world: res.World, iid: int, sigma: float, nseed: int):
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    def actions(active, levels):
        out = []
        for sid in range(len(world.sources)):
            for target in range(levels[sid] + 1, 5):
                if res.useful(world, active, sid, target):
                    out.append((sid, target))
        return out

    @functools.lru_cache(maxsize=None)
    def base(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = actions(active, levels)
        if not acts:
            return math.inf
        sid, target = max(
            acts,
            key=lambda a: (
                res.policy_score(FROZEN_RESOLUTION_ZERO_SHOT, world, active, levels, a[0], a[1], sigma, nseed, iid),
                -res.incremental_cost(world, levels, a[0], a[1]),
            ),
        )
        nl = list(levels)
        nl[sid] = target
        nt = tuple(nl)
        return res.incremental_cost(world, levels, sid, target) + sum(
            p * base(st, nt) for p, st in res.partitions(world, active, sid, target)
        )

    @functools.lru_cache(maxsize=None)
    def rollout(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = actions(active, levels)
        if not acts:
            return math.inf
        ranked = []
        for sid, target in acts:
            nl = list(levels)
            nl[sid] = target
            nt = tuple(nl)
            estimated = res.incremental_cost(world, levels, sid, target) + sum(
                p * base(st, nt) for p, st in res.partitions(world, active, sid, target)
            )
            ranked.append((estimated, res.incremental_cost(world, levels, sid, target), sid, target))
        _estimate, _cost, sid, target = min(ranked)
        nl = list(levels)
        nl[sid] = target
        nt = tuple(nl)
        return res.incremental_cost(world, levels, sid, target) + sum(
            p * rollout(st, nt) for p, st in res.partitions(world, active, sid, target)
        )

    return base(initial_active, initial_levels), rollout(initial_active, initial_levels)


def main() -> None:
    acquisition_worlds = make_acquisition_worlds(120_031, per_family=16)
    acq_base_ratios = []
    acq_rollout_ratios = []
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, inst, opt in acquisition_worlds:
                base, rollout = acquisition_base_and_rollout(inst, iid, sigma, nseed)
                acq_base_ratios.append(base / opt)
                acq_rollout_ratios.append(rollout / opt)

    resolution_worlds = res.make_worlds(120_047, 24)
    res_base_ratios = []
    res_rollout_ratios = []
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, world, opt in resolution_worlds:
                base, rollout = resolution_base_and_rollout(world, iid, sigma, nseed)
                res_base_ratios.append(base / opt)
                res_rollout_ratios.append(rollout / opt)

    result = {
        "experiment": "context-policy-rollout-development-v0.1",
        "status": "development_only_before_freeze",
        "algorithm": "One-step policy rollout / receding-horizon policy improvement. At each state, evaluate every next context action by immediate measured cost plus the frozen base policy's expected remaining cost, choose the minimum, then replan after the observed outcome.",
        "acquisition": {
            "worlds": len(acquisition_worlds),
            "base_frozen_policy": summarize(acq_base_ratios),
            "rollout_policy": summarize(acq_rollout_ratios),
            "mean_cost_reduction_vs_base_pct": round(100 * (1 - statistics.fmean(acq_rollout_ratios) / statistics.fmean(acq_base_ratios)), 2),
        },
        "resolution": {
            "worlds": len(resolution_worlds),
            "base_zero_shot_frozen_acquisition_policy": summarize(res_base_ratios),
            "rollout_policy": summarize(res_rollout_ratios),
            "mean_cost_reduction_vs_base_pct": round(100 * (1 - statistics.fmean(res_rollout_ratios) / statistics.fmean(res_base_ratios)), 2),
        },
        "guardrail": "No sealed-test seed or OOD generator is present here. Freeze the rollout algorithm before introducing unseen worlds.",
        "caveat": "Synthetic model-based controller experiment. The rollout evaluator knows the finite world's transition probabilities; a real agent would need calibrated/sampled outcome and future-cost estimates. This does not establish end-to-end LLM answer quality."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
