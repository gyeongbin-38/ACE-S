#!/usr/bin/env python3
"""Development benchmark for action-agreement adaptive rollout compute.

Instead of using only a heuristic score margin as the difficulty signal, run a
small number of independent one-sample rollout races. If those races choose the
same action with sufficient agreement, commit early; otherwise expand to the
fixed K=8 budget and choose by mean rollout value.

Inspired by the general idea of inter-rollout action agreement as a free
adaptive-compute signal, but implemented here in ACE-S's synthetic context-action
controller mechanics. Development only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

from discover_adaptive_rollout_budget_v2 import (
    MODEL_NOISE_SIGMA,
    VALUE_NOISE_SIGMA,
    base_policy_cost,
    feature_score,
    model_partitions,
    stable_seed,
)
from run_context_action_dominance_bench import dominance_prune, gen_world, partitions

DEV_SEED = 20_611_307
WORLDS = 320
FIXED_K = 8
MAX_ENV_DEGRADATION = 0.01


@dataclass(frozen=True)
class AgreementPolicy:
    pilot_rounds: int
    min_agreement: float
    require_feature_margin: float


def sample_state(model, rng):
    u = rng.random()
    acc = 0.0
    for p, state in model:
        acc += p
        if u <= acc:
            return state
    return model[-1][1]


def choose_fixed(world, subset, seed, base):
    candidates, _ = dominance_prune(world, subset)
    if not candidates:
        return None, 0
    if len(candidates) == 1:
        return candidates[0], 0
    totals = {a: 0.0 for a in candidates}
    for a in candidates:
        model = model_partitions(world, subset, a, seed + 123)
        rng = random.Random(stable_seed("agreement-fixed", seed, subset, a, FIXED_K))
        for _ in range(FIXED_K):
            totals[a] += base(sample_state(model, rng))
    best = min(candidates, key=lambda a: (world.actions[a]["cost"] + totals[a] / FIXED_K, a))
    return best, FIXED_K * len(candidates)


def choose_agreement(world, subset, seed, base, policy: AgreementPolicy):
    candidates, _ = dominance_prune(world, subset)
    if not candidates:
        return None, 0
    if len(candidates) == 1:
        return candidates[0], 0

    feature_rank = sorted(
        ((feature_score(world, subset, a, VALUE_NOISE_SIGMA, seed + 17), a) for a in candidates),
        reverse=True,
    )
    margin = max(feature_rank[0][0], 1e-12) / max(feature_rank[1][0], 1e-12)

    models = {a: model_partitions(world, subset, a, seed + 123) for a in candidates}
    totals = {a: 0.0 for a in candidates}
    votes = {a: 0 for a in candidates}

    # Independent rollout races. Each race draws one modeled future outcome per
    # candidate and selects the lowest one-sample Q action.
    for r in range(policy.pilot_rounds):
        round_q = {}
        for a in candidates:
            rng = random.Random(stable_seed("agreement-pilot", seed, subset, a, r))
            state = sample_state(models[a], rng)
            future = base(state)
            totals[a] += future
            round_q[a] = world.actions[a]["cost"] + future
        winner = min(candidates, key=lambda a: (round_q[a], a))
        votes[winner] += 1

    top_action = max(candidates, key=lambda a: (votes[a], -a))
    agreement = votes[top_action] / policy.pilot_rounds
    samples = policy.pilot_rounds * len(candidates)

    if agreement >= policy.min_agreement and margin >= policy.require_feature_margin:
        # Commit to the action that independently won most pilot races.
        return top_action, samples

    # Disagreement means the state is difficult. Continue each candidate to the
    # same total K=8 samples, reusing pilot samples rather than discarding them.
    for a in candidates:
        for r in range(policy.pilot_rounds, FIXED_K):
            rng = random.Random(stable_seed("agreement-pilot", seed, subset, a, r))
            totals[a] += base(sample_state(models[a], rng))
    samples += (FIXED_K - policy.pilot_rounds) * len(candidates)
    best = min(candidates, key=lambda a: (world.actions[a]["cost"] + totals[a] / FIXED_K, a))
    return best, samples


def evaluate(world, seed, policy):
    base = base_policy_cost(world, seed)
    initial = tuple(range(world.n))

    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset):
            return 0.0, 0.0
        if policy is None:
            action, samples = choose_fixed(world, subset, seed, base)
        else:
            action, samples = choose_agreement(world, subset, seed, base, policy)
        if action is None:
            return float("inf"), float("inf")
        parts = list(partitions(world, subset, action))
        p_self = sum(p for p, st in parts if st == subset)
        if p_self >= 1.0 - 1e-12:
            return float("inf"), float("inf")
        env = world.actions[action]["cost"]
        compute = float(samples)
        for p, st in parts:
            if st == subset:
                continue
            e, c = rec(st)
            env += p * e
            compute += p * c
        return env / (1.0 - p_self), compute / (1.0 - p_self)

    return rec(initial)


def policies():
    out = []
    for pilot in (2, 3, 4):
        for agreement in (0.67, 0.75, 1.0):
            # impossible threshold/pilot combinations are harmless but skip the
            # most redundant cases to keep the search compact.
            if pilot == 2 and agreement == 0.67:
                continue
            for margin in (1.0, 1.05, 1.15, 1.30):
                out.append(AgreementPolicy(pilot, agreement, margin))
    return out


def main():
    rng = random.Random(DEV_SEED)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = [gen_world(rng.randrange(1_000_000_000), families[i % len(families)]) for i in range(WORLDS)]

    valid = []
    fixed_env = []
    fixed_comp = []
    for i, world in enumerate(worlds):
        seed = DEV_SEED + i * 59
        e, c = evaluate(world, seed, None)
        if math.isfinite(e) and math.isfinite(c):
            valid.append((i, world, e, c))
            fixed_env.append(e)
            fixed_comp.append(c)

    base_e = statistics.fmean(fixed_env)
    base_c = statistics.fmean(fixed_comp)
    rows = []
    for policy in policies():
        envs = []
        comps = []
        for i, world, _e, _c in valid:
            e, c = evaluate(world, DEV_SEED + i * 59, policy)
            envs.append(e)
            comps.append(c)
        env_delta = statistics.fmean(envs) / base_e - 1.0
        compute_reduction = 1.0 - statistics.fmean(comps) / base_c
        rows.append((policy, env_delta, compute_reduction, statistics.fmean(envs), statistics.fmean(comps)))

    eligible = [r for r in rows if r[1] <= MAX_ENV_DEGRADATION + 1e-12]
    eligible.sort(key=lambda r: (r[2], -r[1]), reverse=True)
    winner = eligible[0] if eligible else None

    result = {
        "experiment": "agreement-adaptive-rollout-development-v0.1",
        "status": "development_only",
        "worlds": len(valid),
        "candidate_policies": len(rows),
        "max_environment_degradation_pct": 1.0,
        "fixed_k8": {
            "mean_environment_cost": round(base_e, 6),
            "mean_rollout_samples": round(base_c, 3),
        },
        "eligible_policies": len(eligible),
        "selected_policy": asdict(winner[0]) if winner else None,
        "selected": None if winner is None else {
            "environment_cost_change_pct": round(100 * winner[1], 3),
            "rollout_compute_reduction_pct": round(100 * winner[2], 3),
            "mean_environment_cost": round(winner[3], 6),
            "mean_rollout_samples": round(winner[4], 3),
        },
        "top_eligible": [
            {
                "policy": asdict(p),
                "environment_cost_change_pct": round(100 * ed, 3),
                "rollout_compute_reduction_pct": round(100 * cr, 3),
            }
            for p, ed, cr, _e, _c in eligible[:10]
        ],
        "guardrail": "Development only. Freeze before any new sealed generator/seed. The action-agreement signal is synthetic rollout agreement, not calibrated LLM confidence.",
        "claim_boundary": "Tests adaptive controller compute in the synthetic context-action environment. It does not establish equivalent end-to-end LLM answer quality or real tool-call savings.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
