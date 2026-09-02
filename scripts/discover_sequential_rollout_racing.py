#!/usr/bin/env python3
"""Development experiment for sequential best-action rollout racing.

All surviving context actions receive samples round-by-round. After a minimum
number of rounds, the controller forms empirical confidence intervals over
one-step rollout Q values. It stops when the currently best action's upper bound
is below every competitor's lower bound; otherwise it continues up to K=8.

This is a controller-compute experiment, not a formal statistical guarantee:
rollout costs are not assumed Gaussian or bounded by a calibrated real-agent
model. Development only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

from discover_adaptive_rollout_budget_v2 import base_policy_cost, model_partitions, stable_seed
from run_context_action_dominance_bench import dominance_prune, gen_world, partitions

DEV_SEED = 52_801_337
WORLDS = 320
MAX_K = 8
MAX_ENV_DEGRADATION = 0.01


@dataclass(frozen=True)
class RacingPolicy:
    min_rounds: int
    z: float
    min_absolute_gap: float


def sample_state(model, rng):
    u = rng.random()
    acc = 0.0
    for p, state in model:
        acc += p
        if u <= acc:
            return state
    return model[-1][1]


def fixed_choose(world, subset, seed, base):
    candidates, _ = dominance_prune(world, subset)
    if not candidates:
        return None, 0
    if len(candidates) == 1:
        return candidates[0], 0
    sums = {a: 0.0 for a in candidates}
    for a in candidates:
        model = model_partitions(world, subset, a, seed + 123)
        for r in range(MAX_K):
            rng = random.Random(stable_seed("racing", seed, subset, a, r))
            sums[a] += base(sample_state(model, rng))
    best = min(candidates, key=lambda a: (world.actions[a]["cost"] + sums[a] / MAX_K, a))
    return best, MAX_K * len(candidates)


def mean_se(values):
    mean = statistics.fmean(values)
    if len(values) <= 1:
        return mean, math.inf
    sd = statistics.stdev(values)
    return mean, sd / math.sqrt(len(values))


def racing_choose(world, subset, seed, base, policy: RacingPolicy):
    candidates, _ = dominance_prune(world, subset)
    if not candidates:
        return None, 0
    if len(candidates) == 1:
        return candidates[0], 0
    models = {a: model_partitions(world, subset, a, seed + 123) for a in candidates}
    samples = {a: [] for a in candidates}
    total_samples = 0

    for r in range(MAX_K):
        for a in candidates:
            rng = random.Random(stable_seed("racing", seed, subset, a, r))
            future = base(sample_state(models[a], rng))
            samples[a].append(world.actions[a]["cost"] + future)
            total_samples += 1

        rounds = r + 1
        if rounds < policy.min_rounds:
            continue

        stats = {}
        for a in candidates:
            m, se = mean_se(samples[a])
            stats[a] = (m, se)
        best = min(candidates, key=lambda a: (stats[a][0], a))
        best_mean, best_se = stats[best]
        best_upper = best_mean + policy.z * best_se
        separated = True
        for a in candidates:
            if a == best:
                continue
            mean, se = stats[a]
            lower = mean - policy.z * se
            if not (best_upper + policy.min_absolute_gap < lower):
                separated = False
                break
        if separated:
            return best, total_samples

    best = min(candidates, key=lambda a: (statistics.fmean(samples[a]), a))
    return best, total_samples


def evaluate(world, seed, policy):
    base = base_policy_cost(world, seed)
    initial = tuple(range(world.n))

    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0, 0.0
        if policy is None:
            action, samples = fixed_choose(world, subset, seed, base)
        else:
            action, samples = racing_choose(world, subset, seed, base, policy)
        if action is None:
            return math.inf, math.inf
        parts = list(partitions(world, subset, action))
        p_self = sum(p for p, state in parts if state == subset)
        if p_self >= 1.0 - 1e-12:
            return math.inf, math.inf
        env = world.actions[action]["cost"]
        comp = float(samples)
        for p, state in parts:
            if state == subset:
                continue
            e, c = rec(state)
            env += p * e
            comp += p * c
        return env / (1 - p_self), comp / (1 - p_self)

    return rec(initial)


def policies():
    for rounds in (2, 3, 4):
        for z in (0.0, 0.25, 0.5, 0.75, 1.0, 1.5):
            for gap in (0.0, 0.02, 0.05, 0.10):
                yield RacingPolicy(rounds, z, gap)


def main():
    rng = random.Random(DEV_SEED)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = [gen_world(rng.randrange(1_000_000_000), families[i % len(families)]) for i in range(WORLDS)]

    valid = []
    base_envs, base_comps = [], []
    for i, world in enumerate(worlds):
        seed = DEV_SEED + i * 61
        e, c = evaluate(world, seed, None)
        if math.isfinite(e) and math.isfinite(c):
            valid.append((i, world))
            base_envs.append(e)
            base_comps.append(c)
    base_e = statistics.fmean(base_envs)
    base_c = statistics.fmean(base_comps)

    rows = []
    for policy in policies():
        envs, comps = [], []
        for i, world in valid:
            e, c = evaluate(world, DEV_SEED + i * 61, policy)
            envs.append(e); comps.append(c)
        e = statistics.fmean(envs)
        c = statistics.fmean(comps)
        rows.append((policy, e / base_e - 1, 1 - c / base_c, e, c))

    eligible = [r for r in rows if r[1] <= MAX_ENV_DEGRADATION + 1e-12]
    eligible.sort(key=lambda r: (r[2], -r[1]), reverse=True)
    winner = eligible[0] if eligible else None
    result = {
        "experiment": "sequential-rollout-racing-development-v0.1",
        "status": "development_only",
        "worlds": len(valid),
        "candidate_policies": len(rows),
        "fixed_k8": {"mean_environment_cost": round(base_e, 6), "mean_rollout_samples": round(base_c, 3)},
        "max_environment_degradation_pct": 1.0,
        "eligible_policies": len(eligible),
        "selected_policy": asdict(winner[0]) if winner else None,
        "selected": None if winner is None else {
            "environment_cost_change_pct": round(100 * winner[1], 3),
            "rollout_compute_reduction_pct": round(100 * winner[2], 3),
            "mean_environment_cost": round(winner[3], 6),
            "mean_rollout_samples": round(winner[4], 3),
        },
        "top_eligible": [
            {"policy": asdict(p), "environment_cost_change_pct": round(100 * ed, 3), "rollout_compute_reduction_pct": round(100 * cr, 3)}
            for p, ed, cr, _e, _c in eligible[:10]
        ],
        "guardrail": "Development only. The empirical intervals are adaptive-compute heuristics, not formal confidence guarantees. Freeze before introducing a new sealed generator/seed.",
        "claim_boundary": "Synthetic controller rollout economics only; no end-to-end LLM answer-quality or API-call claim.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
