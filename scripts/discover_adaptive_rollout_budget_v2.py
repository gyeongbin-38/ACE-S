#!/usr/bin/env python3
"""Quality-constrained development search for adaptive rollout budgets.

Only policies whose mean environment cost is within +1% of fixed K=8 are eligible.
Among eligible policies, maximize rollout-compute reduction.
Uses SHA-256-derived deterministic RNG seeds independent of PYTHONHASHSEED.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

from run_context_action_dominance_bench import World, dominance_prune, gen_world, partitions

DEV_SEED = 7_711_903
WORLDS = 300
FIXED_K = 8
VALUE_NOISE_SIGMA = 1.0
MODEL_NOISE_SIGMA = 1.0
MAX_ENV_DEGRADATION = 0.01


def stable_seed(*parts: object) -> int:
    payload = "|".join(repr(x) for x in parts).encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def entropy(ps):
    z = sum(ps)
    if z <= 0:
        return 0.0
    return -sum((p / z) * math.log2(p / z) for p in ps if p > 0)


def feature_score(world, subset, action_index, noise_sigma, seed):
    action = world.actions[action_index]
    base_h = entropy([world.priors[i] for i in subset])
    z = world.mass(subset)
    dm = {}
    for i in subset:
        dm[world.decisions[i]] = dm.get(world.decisions[i], 0.0) + world.priors[i] / z
    gini0 = 1.0 - sum(v * v for v in dm.values())
    exp_h = exp_gini = solve_prob = exp_decisions = 0.0
    max_h = 0.0
    for p, state in partitions(world, subset, action_index):
        h = entropy([world.priors[i] for i in state])
        exp_h += p * h
        max_h = max(max_h, h)
        state_z = world.mass(state)
        state_dm = {}
        for i in state:
            state_dm[world.decisions[i]] = state_dm.get(world.decisions[i], 0.0) + world.priors[i] / state_z
        exp_gini += p * (1.0 - sum(v * v for v in state_dm.values()))
        if world.solved(state):
            solve_prob += p
        exp_decisions += p * len({world.decisions[i] for i in state})
    ig = max(0.0, base_h - exp_h)
    gini_gain = max(0.0, gini0 - exp_gini)
    worst_gain = max(0.0, base_h - max_h)
    decision_gain = max(0.0, len(dm) - exp_decisions)
    vals = [ig, gini_gain, solve_prob, worst_gain, decision_gain, action["cost"]]
    rng = random.Random(stable_seed("feature", seed, subset, action_index))
    vals = [x * math.exp(rng.gauss(0.0, noise_sigma)) if x > 0 else 0.0 for x in vals]
    ig, gg, sp, wg, dg, cost = vals
    numerator = (ig ** 0.35 if ig > 0 else 0.0) + gg + 1.5 * sp + 0.5 * wg + 0.5 * dg
    return numerator / (cost ** 1.25 + 1e-12)


def model_partitions(world, subset, action_index, seed):
    parts = list(partitions(world, subset, action_index))
    rng = random.Random(stable_seed("model", seed, subset, action_index))
    weights = [p * math.exp(rng.gauss(0.0, MODEL_NOISE_SIGMA)) for p, _ in parts]
    z = sum(weights)
    return [(w / z, state) for w, (_, state) in zip(weights, parts)]


def base_policy_cost(world, seed):
    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0
        actions, _ = dominance_prune(world, subset)
        if not actions:
            return float("inf")
        action = max(actions, key=lambda a: feature_score(world, subset, a, VALUE_NOISE_SIGMA, seed + 101))
        parts = list(partitions(world, subset, action))
        p_self = sum(p for p, st in parts if st == subset)
        if p_self >= 1 - 1e-12:
            return float("inf")
        rest = sum(p * rec(st) for p, st in parts if st != subset)
        return (world.actions[action]["cost"] + rest) / (1 - p_self)
    return rec


@dataclass(frozen=True)
class Policy:
    greedy_margin: float
    small_margin: float
    small_k: int
    medium_k: int
    hard_k: int


def choose_action(world, subset, seed, base, policy: Policy | None):
    candidates, _ = dominance_prune(world, subset)
    if not candidates:
        return None, 0
    if len(candidates) == 1:
        return candidates[0], 0
    scored = sorted(((feature_score(world, subset, a, VALUE_NOISE_SIGMA, seed + 17), a) for a in candidates), reverse=True)
    margin = max(scored[0][0], 1e-12) / max(scored[1][0], 1e-12)
    if policy is None:
        k = FIXED_K
    elif margin >= policy.greedy_margin:
        k = 0
    elif margin >= policy.small_margin:
        k = policy.small_k
    elif len(candidates) <= 3:
        k = policy.medium_k
    else:
        k = policy.hard_k
    if k == 0:
        return scored[0][1], 0
    best = (float("inf"), None)
    samples = 0
    for _score, action in scored:
        model = model_partitions(world, subset, action, seed + 123)
        cumulative, acc = [], 0.0
        for p, st in model:
            acc += p
            cumulative.append((acc, st))
        rng = random.Random(stable_seed("roll", seed, subset, action, k))
        future = 0.0
        for _ in range(k):
            u = rng.random()
            future += base(next(st for edge, st in cumulative if u <= edge))
        q = world.actions[action]["cost"] + future / k
        samples += k
        if q < best[0]:
            best = (q, action)
    return best[1], samples


def evaluate(world, seed, policy):
    base = base_policy_cost(world, seed)
    initial = tuple(range(world.n))
    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0, 0.0
        action, samples = choose_action(world, subset, seed, base, policy)
        if action is None:
            return float("inf"), float("inf")
        parts = list(partitions(world, subset, action))
        p_self = sum(p for p, st in parts if st == subset)
        if p_self >= 1 - 1e-12:
            return float("inf"), float("inf")
        env, compute = world.actions[action]["cost"], float(samples)
        for p, st in parts:
            if st == subset:
                continue
            e, c = rec(st)
            env += p * e
            compute += p * c
        return env / (1 - p_self), compute / (1 - p_self)
    return rec(initial)


def policies():
    out = []
    for gm in [5.0, 8.0, 12.0, 20.0, 1e9]:
        for sm in [1.05, 1.10, 1.20, 1.35, 1.50]:
            if sm >= gm:
                continue
            for ks in [(2, 6, 8), (4, 6, 8), (4, 8, 8), (6, 8, 8), (4, 6, 10), (6, 8, 12)]:
                out.append(Policy(gm, sm, *ks))
    return out


def main():
    rng = random.Random(DEV_SEED)
    fams = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = [gen_world(rng.randrange(1_000_000_000), fams[i % 4]) for i in range(WORLDS)]
    valid = []
    fixed_env, fixed_comp = [], []
    for i, w in enumerate(worlds):
        e, c = evaluate(w, DEV_SEED + i * 41, None)
        if math.isfinite(e) and math.isfinite(c):
            valid.append((i, w, e, c)); fixed_env.append(e); fixed_comp.append(c)
    base_e, base_c = statistics.fmean(fixed_env), statistics.fmean(fixed_comp)
    rows = []
    for p in policies():
        es, cs = [], []
        for i, w, _e, _c in valid:
            e, c = evaluate(w, DEV_SEED + i * 41, p); es.append(e); cs.append(c)
        ed = statistics.fmean(es) / base_e - 1
        cr = 1 - statistics.fmean(cs) / base_c
        rows.append((p, ed, cr, statistics.fmean(es), statistics.fmean(cs)))
    eligible = [r for r in rows if r[1] <= MAX_ENV_DEGRADATION + 1e-12]
    eligible.sort(key=lambda r: (r[2], -r[1]), reverse=True)
    winner = eligible[0] if eligible else None
    result = {
        "experiment": "adaptive-rollout-budget-search-v0.2",
        "status": "development_quality_constrained",
        "worlds": len(valid),
        "candidate_policies": len(rows),
        "max_environment_degradation_pct": 1.0,
        "fixed_k_baseline": {"mean_environment_cost": round(base_e, 6), "mean_rollout_samples": round(base_c, 3)},
        "eligible_policies": len(eligible),
        "selected_policy": asdict(winner[0]) if winner else None,
        "selected": None if winner is None else {
            "environment_cost_change_pct": round(100 * winner[1], 3),
            "rollout_compute_reduction_pct": round(100 * winner[2], 3),
            "mean_environment_cost": round(winner[3], 6),
            "mean_rollout_samples": round(winner[4], 3),
        },
        "pareto_safe": [
            {"policy": asdict(p), "environment_cost_change_pct": round(100*ed,3), "rollout_compute_reduction_pct": round(100*cr,3)}
            for p, ed, cr, _e, _c in eligible[:10]
        ],
        "guardrail": "Development only. A selected policy must be frozen before a new sealed seed/generator is introduced.",
        "reproducibility": "All stochastic seeds are derived with SHA-256 and are independent of Python process hash randomization."
    }
    print(json.dumps(result, indent=2))
    assert winner is not None


if __name__ == "__main__":
    main()
