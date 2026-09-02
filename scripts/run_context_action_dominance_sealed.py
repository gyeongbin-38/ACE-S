#!/usr/bin/env python3
"""Sealed/OOD test for frozen structural context-action dominance pruning."""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

from scripts.run_context_action_dominance_bench import (
    MODEL_NOISE_SIGMA,
    ROLLOUT_K,
    VALUE_NOISE_SIGMA,
    World,
    dominance_prune,
    evaluate_policy,
    exact_dp,
    feature_score,
    make_rollout_policy,
    partitions,
    useful_actions,
)

FREEZE_COMMIT = "c0493bfad47c17e4ae795e60373d978ee304e4e7"
SEALED_SEED = 9471137
WORLDS = 320


def exact_dp_dynamic_pruned(world):
    @functools.lru_cache(None)
    def dp(subset):
        if world.solved(subset):
            return 0.0
        actions, _ = dominance_prune(world, subset)
        best = float("inf")
        for a in actions:
            parts = list(partitions(world, subset, a))
            p_self = sum(p for p, state in parts if state == subset)
            if p_self >= 1.0 - 1e-12:
                continue
            rest = sum(p * dp(state) for p, state in parts if state != subset)
            best = min(best, (world.actions[a]["cost"] + rest) / (1.0 - p_self))
        return best
    return dp


def random_partition(rng, n, k):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def gen_sealed_world(seed, family):
    rng = random.Random(seed)
    n = rng.randint(5, 8)
    dcount = rng.choice([2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d

    raw = [rng.gammavariate(rng.uniform(0.3, 2.6), 1.0) for _ in range(n)]
    z = sum(raw)
    priors = [x / z for x in raw]

    actions = []
    base_count = rng.randint(7, 11)
    for _ in range(base_count):
        outcomes = random_partition(rng, n, rng.choice([2, 3, 4]))
        if family == "wide_cost":
            cost = math.exp(rng.uniform(math.log(0.25), math.log(14.0)))
        else:
            cost = math.exp(rng.uniform(math.log(0.5), math.log(9.0)))
        actions.append({"cost": cost, "outcomes": outcomes})

    # A direct decision-relevant fallback keeps every world solvable.
    actions.append({"cost": rng.uniform(2.0, 8.0), "outcomes": tuple(decisions)})

    if family == "sparse_redundancy":
        variant_count = rng.randint(2, 5)
    elif family == "cached_refinement":
        variant_count = rng.randint(7, 12)
    elif family == "cross_source_overlap":
        variant_count = rng.randint(8, 14)
    else:
        variant_count = rng.randint(5, 10)

    for _ in range(variant_count):
        src = rng.randrange(len(actions))
        source = actions[src]
        source_out = list(source["outcomes"])

        if family == "cached_refinement" and rng.random() < 0.6:
            # Simulate an already-resident/cached observation: an equally informative
            # action is now cheaper than a redundant remote fetch.
            actions.append({
                "cost": source["cost"] * rng.uniform(0.15, 0.65),
                "outcomes": tuple(source_out),
            })
            actions.append({
                "cost": source["cost"] * rng.uniform(1.1, 2.2),
                "outcomes": tuple(source_out),
            })
            continue

        if family == "cross_source_overlap" and rng.random() < 0.5:
            # Produce a more informative cached/batched view plus a costlier coarser view.
            finer = list(source_out)
            # split one outcome where possible
            groups = defaultdict(list)
            for i, value in enumerate(finer):
                groups[value].append(i)
            splittable = [g for g in groups.values() if len(g) >= 2]
            if splittable:
                group = rng.choice(splittable)
                new_label = max(finer) + 1
                for i in group[len(group)//2:]:
                    finer[i] = new_label
            actions.append({
                "cost": source["cost"] * rng.uniform(0.7, 1.0),
                "outcomes": tuple(finer),
            })
            coarser = list(source_out)
            values = sorted(set(coarser))
            if len(values) >= 2:
                a, b = rng.sample(values, 2)
                coarser = [b if value == a else value for value in coarser]
            actions.append({
                "cost": source["cost"] * rng.uniform(1.15, 2.5),
                "outcomes": tuple(coarser),
            })
            continue

        # Generic duplicate or costly coarsening.
        outcomes = list(source_out)
        if rng.random() < 0.5:
            values = sorted(set(outcomes))
            if len(values) >= 2:
                a, b = rng.sample(values, 2)
                outcomes = [b if value == a else value for value in outcomes]
        actions.append({
            "cost": source["cost"] * rng.uniform(1.05, 3.2),
            "outcomes": tuple(outcomes),
        })

    return World(priors, decisions, actions, family)


def summarize(values):
    ordered = sorted(values)
    def pct(p):
        pos = (len(ordered) - 1) * p
        lo, hi = math.floor(pos), math.ceil(pos)
        if lo == hi:
            return ordered[lo]
        return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)
    return {
        "mean": round(statistics.mean(values), 6),
        "median": round(statistics.median(values), 6),
        "p90": round(pct(0.9), 6),
    }


def main():
    rng = random.Random(SEALED_SEED)
    families = ["sparse_redundancy", "cached_refinement", "cross_source_overlap", "wide_cost"]

    preservation = []
    initial_reduction = []
    no_prune_ratio = []
    prune_ratio = []
    no_prune_samples = []
    prune_samples = []
    by_family = defaultdict(lambda: {"reduction": [], "ratio": [], "samples": []})

    for i in range(WORLDS):
        family = families[i % len(families)]
        world = gen_sealed_world(rng.randrange(1_000_000_000), family)
        initial = tuple(range(world.n))
        full_opt = exact_dp(world)(initial)
        pruned_opt = exact_dp_dynamic_pruned(world)(initial)
        if not (math.isfinite(full_opt) and math.isfinite(pruned_opt)):
            continue
        preservation.append(abs(full_opt - pruned_opt) <= 1e-9)

        keep, _ = dominance_prune(world, initial)
        useful = useful_actions(world, initial)
        reduction = 1.0 - len(keep) / len(useful)
        initial_reduction.append(reduction)

        eval_seed = SEALED_SEED + 101 * i
        env_a, comp_a = evaluate_policy(world, make_rollout_policy(world, eval_seed, prune=False))
        env_b, comp_b = evaluate_policy(world, make_rollout_policy(world, eval_seed, prune=True))
        if not all(math.isfinite(x) for x in (env_a, comp_a, env_b, comp_b)):
            continue
        no_prune_ratio.append(env_a / full_opt)
        prune_ratio.append(env_b / full_opt)
        no_prune_samples.append(comp_a)
        prune_samples.append(comp_b)
        by_family[family]["reduction"].append(reduction)
        by_family[family]["ratio"].append(env_b / full_opt)
        by_family[family]["samples"].append(comp_b)

    result = {
        "experiment": "context-action-dominance-sealed-ood-v0.1",
        "status": "sealed_after_freeze",
        "freeze_commit": FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "worlds_evaluated": len(prune_ratio),
        "dynamic_exact_optimal_preservation_rate_pct": round(100.0 * sum(preservation) / len(preservation), 3),
        "initial_candidate_reduction_pct": round(100.0 * statistics.mean(initial_reduction), 3),
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
                "candidate_reduction_pct": round(100.0 * statistics.mean(data["reduction"]), 3),
                "mean_cost_ratio": round(statistics.mean(data["ratio"]), 6),
                "mean_rollout_samples": round(statistics.mean(data["samples"]), 3),
            }
            for family, data in by_family.items()
        },
        "claim_boundary": (
            "Frozen structural-pruning rule evaluated on post-freeze synthetic OOD generators. "
            "Exactness applies only where refinement and measured costs are structurally known. "
            "Not end-to-end LLM answer-quality evidence."
        ),
    }
    print(json.dumps(result, indent=2))

    assert result["dynamic_exact_optimal_preservation_rate_pct"] == 100.0
    assert result["rollout_compute_reduction_pct"] >= 25.0


if __name__ == "__main__":
    main()
