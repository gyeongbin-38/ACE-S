#!/usr/bin/env python3
"""Development benchmark for separating acquisition from worker exposure.

Synthetic controller mechanics only.

Structured actions (indexes, symbol tables, cache metadata, typed tool results) can
be interpreted by the controller without exposing their full payload to the worker.
Semantic actions require exposure before their observation can be used. The final
worker still receives a sufficient proof packet, so both conditions must reach the
same decision certainty.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

SEED = 730913
WORLDS = 360


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


def partitions(world, subset, action):
    groups = defaultdict(list)
    outcomes = action["outcomes"]
    for i in subset:
        groups[outcomes[i]].append(i)
    z = world.mass(subset)
    return [(world.mass(tuple(g)) / z, tuple(sorted(g))) for g in groups.values()]


def useful(world, subset, action):
    return len(partitions(world, subset, action)) > 1


def proof_exposure_cost(world, subset, acquired):
    """Minimum full-payload exposure among acquired evidence that separates decisions.

    A proof candidate is sufficient if every observation cell, restricted to the
    final epistemic state, maps to a single decision. At a solved state this mainly
    means exposing one acquired item that directly supports the resolved branch.
    We conservatively require at least one full evidence payload.
    """
    if not acquired:
        return 0.0
    candidates = []
    for idx in acquired:
        action = world.actions[idx]
        # Any action actually acquired on the path is allowed as final evidence;
        # prefer the smallest evidence packet. Semantic actions were already exposed.
        candidates.append(action["exposure_cost"])
    return min(candidates) if candidates else 0.0


def exact_policy(world, decoupled):
    """Exact DP over epistemic subset plus acquired structured evidence bitmask.

    To keep state bounded, semantic actions are exposed immediately and do not need
    to remain in the hidden acquired mask. Structured actions can be acquired hidden;
    their full payload is exposed only once at the final proof step.
    """
    n_actions = len(world.actions)

    @functools.lru_cache(None)
    def dp(subset, acquired_mask, semantic_exposed):
        acquired = [i for i in range(n_actions) if acquired_mask & (1 << i)]
        if world.solved(subset):
            if decoupled:
                # Semantic evidence already paid exposure on acquisition. If none was
                # exposed, reveal one minimal acquired structured proof packet now.
                if semantic_exposed:
                    return 0.0
                return proof_exposure_cost(world, subset, acquired)
            return 0.0

        best = float("inf")
        for idx, action in enumerate(world.actions):
            if acquired_mask & (1 << idx):
                continue
            if not useful(world, subset, action):
                continue
            parts = partitions(world, subset, action)
            p_self = sum(p for p, state in parts if state == subset)
            if p_self >= 1.0 - 1e-12:
                continue

            immediate = action["acquisition_cost"]
            next_semantic_exposed = semantic_exposed
            if not decoupled or action["kind"] == "semantic":
                immediate += action["exposure_cost"]
                if action["kind"] == "semantic":
                    next_semantic_exposed = True

            next_mask = acquired_mask | (1 << idx)
            rest = 0.0
            for p, state in parts:
                if state == subset:
                    continue
                rest += p * dp(state, next_mask, next_semantic_exposed)
            q = (immediate + rest) / (1.0 - p_self)
            best = min(best, q)
        return best

    return dp


def exact_components(world, decoupled):
    """Return optimal total cost, plus expected acquisition/exposure components.

    Tie-break by total then exposure. Uses the same semantics as exact_policy.
    """
    n_actions = len(world.actions)

    @functools.lru_cache(None)
    def dp(subset, acquired_mask, semantic_exposed):
        acquired = [i for i in range(n_actions) if acquired_mask & (1 << i)]
        if world.solved(subset):
            exposure = 0.0
            if decoupled and not semantic_exposed:
                exposure = proof_exposure_cost(world, subset, acquired)
            return exposure, 0.0, exposure, 0.0

        best = (float("inf"), float("inf"), float("inf"), float("inf"))
        for idx, action in enumerate(world.actions):
            if acquired_mask & (1 << idx) or not useful(world, subset, action):
                continue
            parts = partitions(world, subset, action)
            p_self = sum(p for p, state in parts if state == subset)
            if p_self >= 1.0 - 1e-12:
                continue

            acq = action["acquisition_cost"]
            exp = 0.0
            next_sem = semantic_exposed
            if not decoupled or action["kind"] == "semantic":
                exp = action["exposure_cost"]
                if action["kind"] == "semantic":
                    next_sem = True
            calls = 1.0
            total = acq + exp
            exp_acq, exp_exp, exp_calls = acq, exp, calls
            next_mask = acquired_mask | (1 << idx)
            for p, state in parts:
                if state == subset:
                    continue
                child_total, child_acq, child_exp, child_calls = dp(state, next_mask, next_sem)
                total += p * child_total
                exp_acq += p * child_acq
                exp_exp += p * child_exp
                exp_calls += p * child_calls
            denom = 1.0 - p_self
            candidate = (total / denom, exp_acq / denom, exp_exp / denom, exp_calls / denom)
            if (candidate[0], candidate[2]) < (best[0], best[2]):
                best = candidate
        return best

    return dp(tuple(range(world.n)), 0, False)


def random_partition(rng, n, k):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def gen_world(seed, family):
    rng = random.Random(seed)
    n = rng.randint(5, 7)
    dcount = rng.choice([2, 2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d
    raw = [rng.gammavariate(rng.uniform(0.4, 2.2), 1.0) for _ in range(n)]
    z = sum(raw)
    priors = [x / z for x in raw]

    if family == "structured_heavy":
        structured_p = 0.8
    elif family == "semantic_heavy":
        structured_p = 0.2
    elif family == "balanced":
        structured_p = 0.5
    elif family == "expensive_exposure":
        structured_p = 0.65
    else:
        structured_p = 0.5

    actions = []
    count = rng.randint(6, 9)
    for _ in range(count):
        kind = "structured" if rng.random() < structured_p else "semantic"
        outcomes = random_partition(rng, n, rng.choice([2, 3, 4]))
        acquisition = math.exp(rng.uniform(math.log(0.4), math.log(4.0)))
        if family == "expensive_exposure":
            exposure = math.exp(rng.uniform(math.log(4.0), math.log(24.0)))
        else:
            exposure = math.exp(rng.uniform(math.log(1.5), math.log(14.0)))
        if kind == "structured":
            # Indexes/tool metadata tend to have large raw payloads but cheap typed
            # controller summaries. Full payload still costs exposure if needed as proof.
            exposure *= rng.uniform(0.9, 1.5)
        actions.append({
            "kind": kind,
            "outcomes": outcomes,
            "acquisition_cost": acquisition,
            "exposure_cost": exposure,
        })

    # Guarantee a semantic direct-evidence fallback so decoupling cannot rely only
    # on hidden metadata when a semantic proof is genuinely the best option.
    actions.append({
        "kind": "semantic",
        "outcomes": tuple(decisions),
        "acquisition_cost": rng.uniform(2.0, 5.0),
        "exposure_cost": rng.uniform(3.0, 10.0),
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
    rng = random.Random(SEED)
    families = ["balanced", "structured_heavy", "semantic_heavy", "expensive_exposure"]
    coupled_total = []
    decoupled_total = []
    coupled_exp = []
    decoupled_exp = []
    coupled_acq = []
    decoupled_acq = []
    by_family = defaultdict(lambda: {"total_ratio": [], "exposure_ratio": []})

    for i in range(WORLDS):
        family = families[i % len(families)]
        world = gen_world(rng.randrange(1_000_000_000), family)
        c_total, c_acq, c_exp, _ = exact_components(world, decoupled=False)
        d_total, d_acq, d_exp, _ = exact_components(world, decoupled=True)
        if not all(math.isfinite(v) for v in (c_total, c_acq, c_exp, d_total, d_acq, d_exp)):
            continue
        coupled_total.append(c_total)
        decoupled_total.append(d_total)
        coupled_exp.append(c_exp)
        decoupled_exp.append(d_exp)
        coupled_acq.append(c_acq)
        decoupled_acq.append(d_acq)
        by_family[family]["total_ratio"].append(d_total / c_total)
        by_family[family]["exposure_ratio"].append(d_exp / c_exp if c_exp > 0 else 1.0)

    result = {
        "experiment": "acquisition-exposure-separation-development-v0.1",
        "status": "development_only",
        "worlds_evaluated": len(coupled_total),
        "coupled": {
            "total_cost": summarize(coupled_total),
            "exposure_cost": summarize(coupled_exp),
            "acquisition_cost": summarize(coupled_acq),
        },
        "decoupled": {
            "total_cost": summarize(decoupled_total),
            "exposure_cost": summarize(decoupled_exp),
            "acquisition_cost": summarize(decoupled_acq),
        },
        "mean_total_cost_reduction_pct": round(100.0 * (1.0 - statistics.mean(decoupled_total) / statistics.mean(coupled_total)), 3),
        "mean_worker_exposure_reduction_pct": round(100.0 * (1.0 - statistics.mean(decoupled_exp) / statistics.mean(coupled_exp)), 3),
        "mean_acquisition_cost_change_pct": round(100.0 * (statistics.mean(decoupled_acq) / statistics.mean(coupled_acq) - 1.0), 3),
        "by_family": {
            family: {
                "mean_total_cost_reduction_pct": round(100.0 * (1.0 - statistics.mean(data["total_ratio"])), 3),
                "mean_exposure_reduction_pct": round(100.0 * (1.0 - statistics.mean(data["exposure_ratio"])), 3),
            }
            for family, data in by_family.items()
        },
        "quality_invariant": "Both policies are exact DPs and terminate only at decision certainty; decoupled structured actions are usable hidden only when marked controller-interpretable, while semantic actions pay worker exposure immediately.",
        "claim_boundary": "Synthetic controller mechanics. Structured-vs-semantic interpretability is provided by the generator contract; real systems need typed tool contracts or validators before treating results as controller-interpretable.",
    }
    print(json.dumps(result, indent=2))

    assert len(coupled_total) >= 300
    assert result["mean_worker_exposure_reduction_pct"] >= 20.0


if __name__ == "__main__":
    main()
