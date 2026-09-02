#!/usr/bin/env python3
"""Development benchmark for structural context-action dominance pruning.

This benchmark asks a narrow controller-mechanics question:
Can ACE-S deterministically remove context actions that are strictly dominated
by another action that is no more expensive and whose observation partition is
at least as informative?

Synthetic only. Not end-to-end LLM evidence.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

DEV_SEED = 581203
WORLDS = 240
ROLLOUT_K = 8
VALUE_NOISE_SIGMA = 1.0
MODEL_NOISE_SIGMA = 1.0


def entropy(ps):
    z = sum(ps)
    if z <= 0:
        return 0.0
    return -sum((p / z) * math.log2(p / z) for p in ps if p > 0)


class World:
    def __init__(self, priors, decisions, actions, family):
        self.priors = tuple(priors)
        self.decisions = tuple(decisions)
        self.actions = actions
        self.family = family
        self.n = len(priors)

    def mass(self, subset):
        return sum(self.priors[i] for i in subset)

    def solved(self, subset):
        return len({self.decisions[i] for i in subset}) <= 1


def partitions(world, subset, action_index):
    groups = defaultdict(list)
    outcomes = world.actions[action_index]["outcomes"]
    for i in subset:
        groups[outcomes[i]].append(i)
    z = world.mass(subset)
    for group in groups.values():
        state = tuple(sorted(group))
        yield world.mass(state) / z, state


def useful_actions(world, subset):
    return [
        i for i in range(len(world.actions))
        if len(list(partitions(world, subset, i))) > 1
    ]


def refines(world, subset, better, worse):
    """True iff better's observation partition refines worse on this state."""
    better_out = world.actions[better]["outcomes"]
    worse_out = world.actions[worse]["outcomes"]
    groups = defaultdict(list)
    for i in subset:
        groups[better_out[i]].append(i)
    for group in groups.values():
        if len({worse_out[i] for i in group}) > 1:
            return False
    return True


def dominance_prune(world, subset):
    """Remove actions dominated by a no-costlier, at-least-as-informative action."""
    actions = useful_actions(world, subset)
    keep = []
    dominated = {}
    for a in actions:
        ca = world.actions[a]["cost"]
        dominators = []
        for b in actions:
            if a == b:
                continue
            cb = world.actions[b]["cost"]
            if cb <= ca + 1e-12 and refines(world, subset, b, a):
                strictly_better = (
                    cb < ca - 1e-12
                    or not refines(world, subset, a, b)
                    or b < a
                )
                if strictly_better:
                    dominators.append(b)
        if dominators:
            dominated[a] = min(dominators, key=lambda x: world.actions[x]["cost"])
        else:
            keep.append(a)
    return keep, dominated


def exact_dp(world):
    @functools.lru_cache(None)
    def dp(subset):
        if world.solved(subset):
            return 0.0
        best = float("inf")
        for a in useful_actions(world, subset):
            parts = list(partitions(world, subset, a))
            p_self = sum(p for p, state in parts if state == subset)
            if p_self >= 1.0 - 1e-12:
                continue
            rest = sum(p * dp(state) for p, state in parts if state != subset)
            q = (world.actions[a]["cost"] + rest) / (1.0 - p_self)
            best = min(best, q)
        return best
    return dp


def feature_score(world, subset, action_index, noise_sigma, seed):
    action = world.actions[action_index]
    base_h = entropy([world.priors[i] for i in subset])
    z = world.mass(subset)
    dm = defaultdict(float)
    for i in subset:
        dm[world.decisions[i]] += world.priors[i] / z
    gini0 = 1.0 - sum(v * v for v in dm.values())
    exp_h = exp_gini = solve_prob = exp_decisions = 0.0
    max_h = 0.0
    for p, state in partitions(world, subset, action_index):
        h = entropy([world.priors[i] for i in state])
        exp_h += p * h
        max_h = max(max_h, h)
        state_z = world.mass(state)
        state_dm = defaultdict(float)
        for i in state:
            state_dm[world.decisions[i]] += world.priors[i] / state_z
        exp_gini += p * (1.0 - sum(v * v for v in state_dm.values()))
        if world.solved(state):
            solve_prob += p
        exp_decisions += p * len({world.decisions[i] for i in state})

    ig = max(0.0, base_h - exp_h)
    gini_gain = max(0.0, gini0 - exp_gini)
    worst_gain = max(0.0, base_h - max_h)
    decision_gain = max(0.0, len(dm) - exp_decisions)
    cost = action["cost"]

    rng = random.Random(hash((seed, subset, action_index)) & 0xFFFFFFFF)
    def noisy(x):
        return x * math.exp(rng.gauss(0.0, noise_sigma)) if x > 0 else 0.0

    ig, gini_gain, solve_prob, worst_gain, decision_gain, cost = [
        noisy(x) for x in (ig, gini_gain, solve_prob, worst_gain, decision_gain, cost)
    ]
    numerator = (
        (ig ** 0.35 if ig > 0 else 0.0)
        + gini_gain
        + 1.5 * solve_prob
        + 0.5 * worst_gain
        + 0.5 * decision_gain
    )
    return numerator / (cost ** 1.25 + 1e-12)


def base_policy_cost(world, seed):
    @functools.lru_cache(None)
    def cost(subset):
        if world.solved(subset):
            return 0.0
        actions = useful_actions(world, subset)
        if not actions:
            return float("inf")
        selected = max(
            actions,
            key=lambda a: feature_score(world, subset, a, VALUE_NOISE_SIGMA, seed + 991),
        )
        parts = list(partitions(world, subset, selected))
        p_self = sum(p for p, state in parts if state == subset)
        if p_self >= 1.0 - 1e-12:
            return float("inf")
        rest = sum(p * cost(state) for p, state in parts if state != subset)
        return (world.actions[selected]["cost"] + rest) / (1.0 - p_self)
    return cost


def model_partitions(world, subset, action_index, seed):
    parts = list(partitions(world, subset, action_index))
    rng = random.Random(hash(("model", seed, subset, action_index)) & 0xFFFFFFFF)
    weights = [p * math.exp(rng.gauss(0.0, MODEL_NOISE_SIGMA)) for p, _ in parts]
    z = sum(weights)
    return [(w / z, state) for w, (_, state) in zip(weights, parts)]


def make_rollout_policy(world, seed, prune):
    base = base_policy_cost(world, seed)

    def choose(subset):
        if prune:
            candidates, _ = dominance_prune(world, subset)
        else:
            candidates = useful_actions(world, subset)
        if not candidates:
            return None, 0

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
            rng = random.Random(hash(("roll", seed, subset, action, ROLLOUT_K)) & 0xFFFFFFFF)
            future = 0.0
            for _ in range(ROLLOUT_K):
                u = rng.random()
                state = next(state for edge, state in cumulative if u <= edge)
                future += base(state)
            q = world.actions[action]["cost"] + future / ROLLOUT_K
            samples += ROLLOUT_K
            if q < best_q:
                best_q = q
                best_action = action
        return best_action, samples

    return choose


def evaluate_policy(world, choose):
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
            next_env, next_compute = rec(state)
            env += p * next_env
            compute += p * next_compute
        return env / (1.0 - p_self), compute / (1.0 - p_self)

    return rec(initial)


def gen_world(seed, family):
    rng = random.Random(seed)
    n = rng.randint(5, 8)
    dcount = rng.choice([2, 2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d
    raw = [rng.gammavariate(rng.uniform(0.4, 2.0), 1.0) for _ in range(n)]
    z = sum(raw)
    priors = [x / z for x in raw]

    actions = []
    base_count = rng.randint(6, 9)
    for _ in range(base_count):
        k = rng.choice([2, 2, 3, 4])
        outcomes = [rng.randrange(k) for _ in range(n)]
        if len(set(outcomes)) < 2:
            outcomes[0], outcomes[-1] = 0, 1
        cost = math.exp(rng.uniform(math.log(0.5), math.log(8.0)))
        actions.append({"cost": cost, "outcomes": tuple(outcomes)})

    # Ensure at least one directly decision-relevant action exists.
    actions.append({"cost": rng.uniform(1.5, 6.0), "outcomes": tuple(decisions)})

    # Add structurally redundant variants. These emulate duplicate search hits,
    # strictly coarser summaries that cost more, stale duplicate capabilities,
    # or already-cached finer evidence that makes a coarser fetch unnecessary.
    if family == "light_redundancy":
        variants = rng.randint(3, 6)
    elif family == "heavy_redundancy":
        variants = rng.randint(12, 18)
    elif family == "costly_coarse":
        variants = rng.randint(8, 14)
    else:
        variants = rng.randint(6, 12)

    for _ in range(variants):
        base = rng.randrange(len(actions))
        source = actions[base]
        outcomes = list(source["outcomes"])
        kind = "coarser" if family == "costly_coarse" or rng.random() < 0.45 else "duplicate"
        if kind == "coarser":
            values = sorted(set(outcomes))
            if len(values) >= 2:
                src, dst = rng.sample(values, 2)
                outcomes = [dst if value == src else value for value in outcomes]
        multiplier = rng.uniform(1.05, 2.8)
        actions.append({"cost": source["cost"] * multiplier, "outcomes": tuple(outcomes)})

    return World(priors, decisions, actions, family)


def summarize(values):
    ordered = sorted(values)
    def pct(p):
        if not ordered:
            return float("nan")
        index = (len(ordered) - 1) * p
        lo, hi = math.floor(index), math.ceil(index)
        if lo == hi:
            return ordered[lo]
        return ordered[lo] * (hi - index) + ordered[hi] * (index - lo)
    return {
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "p90": round(pct(0.90), 6),
    }


def main():
    rng = random.Random(DEV_SEED)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]

    exact_preserved = 0
    exact_checked = 0
    candidate_reduction = []
    no_prune_ratio = []
    prune_ratio = []
    no_prune_samples = []
    prune_samples = []
    by_family = defaultdict(lambda: {"candidate_reduction": [], "prune_ratio": [], "samples": []})

    for i in range(WORLDS):
        family = families[i % len(families)]
        world = gen_world(rng.randrange(1_000_000_000), family)
        initial = tuple(range(world.n))
        optimal = exact_dp(world)(initial)
        if not math.isfinite(optimal):
            continue

        keep, _ = dominance_prune(world, initial)
        useful = useful_actions(world, initial)
        candidate_reduction.append(1.0 - len(keep) / len(useful))

        pruned_world = World(
            world.priors,
            world.decisions,
            [world.actions[j] for j in keep],
            world.family,
        )
        pruned_optimal = exact_dp(pruned_world)(tuple(range(pruned_world.n)))
        exact_checked += 1
        if abs(pruned_optimal - optimal) <= 1e-9:
            exact_preserved += 1

        seed = DEV_SEED + i * 17
        env_a, comp_a = evaluate_policy(world, make_rollout_policy(world, seed, prune=False))
        env_b, comp_b = evaluate_policy(world, make_rollout_policy(world, seed, prune=True))
        if all(math.isfinite(x) for x in (env_a, comp_a, env_b, comp_b)):
            no_prune_ratio.append(env_a / optimal)
            prune_ratio.append(env_b / optimal)
            no_prune_samples.append(comp_a)
            prune_samples.append(comp_b)
            by_family[family]["candidate_reduction"].append(candidate_reduction[-1])
            by_family[family]["prune_ratio"].append(env_b / optimal)
            by_family[family]["samples"].append(comp_b)

    result = {
        "experiment": "context-action-dominance-development-v0.1",
        "status": "development_only",
        "worlds_requested": WORLDS,
        "worlds_evaluated": len(prune_ratio),
        "exact_optimal_preservation_rate_pct": round(100.0 * exact_preserved / exact_checked, 3),
        "initial_candidate_reduction_pct": round(100.0 * statistics.mean(candidate_reduction), 3),
        "without_pruning": {
            "cost_ratio_to_exact_optimal": summarize(no_prune_ratio),
            "mean_rollout_samples": round(statistics.mean(no_prune_samples), 3),
        },
        "with_structural_dominance_pruning": {
            "cost_ratio_to_exact_optimal": summarize(prune_ratio),
            "mean_rollout_samples": round(statistics.mean(prune_samples), 3),
        },
        "rollout_compute_reduction_pct": round(
            100.0 * (1.0 - statistics.mean(prune_samples) / statistics.mean(no_prune_samples)), 3
        ),
        "mean_environment_cost_change_pct": round(
            100.0 * (statistics.mean(prune_ratio) / statistics.mean(no_prune_ratio) - 1.0), 3
        ),
        "by_family": {
            family: {
                "candidate_reduction_pct": round(100.0 * statistics.mean(data["candidate_reduction"]), 3),
                "mean_cost_ratio": round(statistics.mean(data["prune_ratio"]), 6),
                "mean_rollout_samples": round(statistics.mean(data["samples"]), 3),
            }
            for family, data in by_family.items()
        },
        "claim_boundary": (
            "Synthetic finite-decision controller mechanics only. Structural dominance is exact only "
            "when partition refinement and non-higher measured cost are known, not merely predicted semantically."
        ),
    }

    print(json.dumps(result, indent=2))

    assert result["exact_optimal_preservation_rate_pct"] == 100.0
    assert result["initial_candidate_reduction_pct"] >= 30.0
    assert result["rollout_compute_reduction_pct"] >= 30.0


if __name__ == "__main__":
    main()
