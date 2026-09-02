#!/usr/bin/env python3
"""Development search for adaptive rollout-budget allocation after dominance pruning.

Goal: spend controller rollout samples only on ambiguous action-frontier states while
preserving environment-cost quality relative to fixed-K rollout.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

from run_context_action_dominance_bench import (
    World,
    dominance_prune,
    feature_score,
    gen_world,
    model_partitions,
    partitions,
)

DEV_SEED = 6_208_117
WORLDS = 260
FIXED_K = 8
VALUE_NOISE = 1.0


@dataclass(frozen=True)
class BudgetPolicy:
    greedy_margin: float
    small_margin: float
    small_k: int
    medium_k: int
    hard_k: int


def base_policy_cost(world: World, seed: int):
    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0
        actions, _ = dominance_prune(world, subset)
        if not actions:
            return float("inf")
        selected = max(
            actions,
            key=lambda a: feature_score(world, subset, a, VALUE_NOISE, seed + 991),
        )
        parts = list(partitions(world, subset, selected))
        p_self = sum(p for p, state in parts if state == subset)
        if p_self >= 1.0 - 1e-12:
            return float("inf")
        rest = sum(p * rec(state) for p, state in parts if state != subset)
        return (world.actions[selected]["cost"] + rest) / (1.0 - p_self)
    return rec


def choose_with_k(world, subset, candidates, seed, k, base):
    if not candidates:
        return None, 0
    if k <= 0:
        selected = max(
            candidates,
            key=lambda a: feature_score(world, subset, a, VALUE_NOISE, seed + 17),
        )
        return selected, 0

    best_action = None
    best_q = float("inf")
    samples = 0
    for action in candidates:
        model = model_partitions(world, subset, action, seed + 123)
        cumulative = []
        total = 0.0
        for p, state in model:
            total += p
            cumulative.append((total, state))
        rng = random.Random(hash(("adaptive-roll", seed, subset, action, k)) & 0xFFFFFFFF)
        future = 0.0
        for _ in range(k):
            u = rng.random()
            state = next(state for edge, state in cumulative if u <= edge)
            future += base(state)
        q = world.actions[action]["cost"] + future / k
        samples += k
        if q < best_q:
            best_q = q
            best_action = action
    return best_action, samples


def make_policy(world, seed, budget: BudgetPolicy | None):
    base = base_policy_cost(world, seed)

    def choose(subset):
        candidates, _ = dominance_prune(world, subset)
        if not candidates:
            return None, 0
        if len(candidates) == 1:
            return candidates[0], 0

        scored = sorted(
            ((feature_score(world, subset, a, VALUE_NOISE, seed + 17), a) for a in candidates),
            reverse=True,
        )
        top = max(scored[0][0], 1e-12)
        second = max(scored[1][0], 1e-12)
        margin = top / second

        if budget is None:
            k = FIXED_K
        elif margin >= budget.greedy_margin:
            k = 0
        elif margin >= budget.small_margin:
            k = budget.small_k
        elif len(candidates) <= 3:
            k = budget.medium_k
        else:
            k = budget.hard_k
        return choose_with_k(world, subset, candidates, seed, k, base)

    return choose


def evaluate(world, choose):
    initial = tuple(range(world.n))

    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0, 0.0
        action, samples = choose(subset)
        if action is None:
            return float("inf"), float("inf")
        parts = list(partitions(world, subset, action))
        p_self = sum(p for p, state in parts if state == subset)
        if p_self >= 1.0 - 1e-12:
            return float("inf"), float("inf")
        env = world.actions[action]["cost"]
        compute = float(samples)
        for p, state in parts:
            if state == subset:
                continue
            e, c = rec(state)
            env += p * e
            compute += p * c
        return env / (1.0 - p_self), compute / (1.0 - p_self)

    return rec(initial)


def candidate_policies():
    out = []
    for greedy in [1.5, 2.0, 3.0, 5.0]:
        for small_margin in [1.15, 1.3, 1.5]:
            if small_margin >= greedy:
                continue
            for small_k, medium_k, hard_k in [(2, 4, 8), (2, 6, 8), (4, 6, 8), (2, 4, 12)]:
                out.append(BudgetPolicy(greedy, small_margin, small_k, medium_k, hard_k))
    return out


def main():
    rng = random.Random(DEV_SEED)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = []
    for i in range(WORLDS):
        worlds.append(gen_world(rng.randrange(1_000_000_000), families[i % len(families)]))

    fixed_env, fixed_compute = [], []
    valid_worlds = []
    for i, world in enumerate(worlds):
        env, comp = evaluate(world, make_policy(world, DEV_SEED + i * 31, None))
        if math.isfinite(env) and math.isfinite(comp):
            valid_worlds.append((i, world))
            fixed_env.append(env)
            fixed_compute.append(comp)

    baseline_env = statistics.fmean(fixed_env)
    baseline_compute = statistics.fmean(fixed_compute)

    rows = []
    for policy in candidate_policies():
        envs, comps = [], []
        worse = []
        for i, world in valid_worlds:
            env, comp = evaluate(world, make_policy(world, DEV_SEED + i * 31, policy))
            envs.append(env); comps.append(comp)
        env_mean = statistics.fmean(envs)
        comp_mean = statistics.fmean(comps)
        env_delta = env_mean / baseline_env - 1.0
        compute_reduction = 1.0 - comp_mean / baseline_compute
        # Quality-first selection: strongly penalize environment degradation above 1%.
        objective = compute_reduction - 8.0 * max(0.0, env_delta - 0.01) - 2.0 * max(0.0, env_delta)
        rows.append((objective, policy, env_delta, compute_reduction, env_mean, comp_mean))

    rows.sort(key=lambda x: x[0], reverse=True)
    winner = rows[0]
    result = {
        "experiment": "adaptive-rollout-budget-search-v0.1",
        "status": "development_search_only",
        "worlds": len(valid_worlds),
        "fixed_k": FIXED_K,
        "candidate_policies": len(rows),
        "fixed_k_baseline": {
            "mean_environment_cost": round(baseline_env, 6),
            "mean_rollout_samples": round(baseline_compute, 3),
        },
        "selected_policy": asdict(winner[1]),
        "selected": {
            "mean_environment_cost": round(winner[4], 6),
            "environment_cost_change_pct": round(100.0 * winner[2], 3),
            "mean_rollout_samples": round(winner[5], 3),
            "rollout_compute_reduction_pct": round(100.0 * winner[3], 3),
        },
        "top_candidates": [
            {
                "policy": asdict(policy),
                "environment_cost_change_pct": round(100.0 * env_delta, 3),
                "rollout_compute_reduction_pct": round(100.0 * comp_red, 3),
                "objective": round(obj, 6),
            }
            for obj, policy, env_delta, comp_red, _env, _comp in rows[:8]
        ],
        "guardrail": "Development search only. Freeze the selected budget policy before introducing new OOD generator families/seeds.",
        "claim_boundary": "Synthetic controller mechanics; margins are derived from the noisy heuristic score, not calibrated real-agent uncertainty."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
