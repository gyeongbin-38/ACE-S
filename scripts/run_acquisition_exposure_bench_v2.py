#!/usr/bin/env python3
"""Corrected development benchmark for acquisition/exposure plane separation.

Tracks controller epistemic state and worker-visible epistemic state separately.
A run terminates only when BOTH controller and worker are decision-sufficient.
Structured evidence may be acquired hidden, but it must later be exposed (or be
replaced by other exposed evidence) before the worker is allowed to answer.

Synthetic controller mechanics only; not end-to-end LLM evidence.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

SEED = 811237
WORLDS = 220


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


def groups_for_action(world, subset, action_index):
    groups = defaultdict(list)
    outcomes = world.actions[action_index]["outcomes"]
    for i in subset:
        groups[outcomes[i]].append(i)
    return {outcome: tuple(sorted(group)) for outcome, group in groups.items()}


def partitions(world, subset, action_index):
    groups = groups_for_action(world, subset, action_index)
    z = world.mass(subset)
    return [
        (world.mass(state) / z, outcome, state)
        for outcome, state in groups.items()
    ]


def worker_update(world, worker_subset, action_index, observed_outcome):
    outcomes = world.actions[action_index]["outcomes"]
    narrowed = tuple(i for i in worker_subset if outcomes[i] == observed_outcome)
    return narrowed


def coupled_exact(world):
    """Every acquisition is immediately exposed to the worker."""
    n_actions = len(world.actions)

    @functools.lru_cache(None)
    def dp(subset, used_mask):
        if world.solved(subset):
            return 0.0, 0.0, 0.0, 0.0
        best = (float("inf"), float("inf"), float("inf"), float("inf"))
        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, subset, idx)
            if len(parts) <= 1:
                continue
            immediate_acq = action["acquisition_cost"]
            immediate_exp = action["exposure_cost"]
            total = immediate_acq + immediate_exp
            acq, exp, calls = immediate_acq, immediate_exp, 1.0
            next_mask = used_mask | (1 << idx)
            for p, _outcome, state in parts:
                child_total, child_acq, child_exp, child_calls = dp(state, next_mask)
                total += p * child_total
                acq += p * child_acq
                exp += p * child_exp
                calls += p * child_calls
            candidate = (total, acq, exp, calls)
            if (candidate[0], candidate[2]) < (best[0], best[2]):
                best = candidate
        return best

    return dp(tuple(range(world.n)), 0)


def decoupled_exact(world):
    """Structured acquisitions may stay controller-only until selectively exposed.

    State:
      controller_subset: what the controller knows
      worker_subset:     what the worker can infer from exposed evidence
      used_mask:         already acquired actions
      hidden_mask:       acquired structured actions not yet exposed
    """
    n_actions = len(world.actions)

    @functools.lru_cache(None)
    def dp(controller_subset, worker_subset, used_mask, hidden_mask):
        if world.solved(controller_subset) and world.solved(worker_subset):
            return 0.0, 0.0, 0.0, 0.0

        best = (float("inf"), float("inf"), float("inf"), float("inf"))

        # 1) Expose a previously acquired structured item. Its observed outcome is
        # known to the controller because controller_subset lies in one observation cell.
        for idx in range(n_actions):
            if not (hidden_mask & (1 << idx)):
                continue
            outcomes = world.actions[idx]["outcomes"]
            observed = {outcomes[i] for i in controller_subset}
            if len(observed) != 1:
                # Should not occur for an actually acquired hidden action; reject if it does.
                continue
            observed_outcome = next(iter(observed))
            narrowed_worker = worker_update(world, worker_subset, idx, observed_outcome)
            if narrowed_worker == worker_subset:
                # Exposing evidence that changes no worker uncertainty can still serve
                # provenance, but this decision benchmark has no separate provenance goal.
                continue
            child = dp(
                controller_subset,
                narrowed_worker,
                used_mask,
                hidden_mask & ~(1 << idx),
            )
            exp_cost = world.actions[idx]["exposure_cost"]
            candidate = (
                exp_cost + child[0],
                child[1],
                exp_cost + child[2],
                child[3],
            )
            if (candidate[0], candidate[2]) < (best[0], best[2]):
                best = candidate

        # 2) Acquire a new action. Structured results narrow controller state only;
        # semantic results are exposed immediately and narrow both states.
        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, controller_subset, idx)
            if len(parts) <= 1:
                # If controller already knows the outcome, a semantic action can still
                # be acquired/exposed as cheap proof to narrow worker state.
                outcomes = action["outcomes"]
                known_outcomes = {outcomes[i] for i in controller_subset}
                if action["kind"] != "semantic" or len(known_outcomes) != 1:
                    continue
                observed = next(iter(known_outcomes))
                narrowed_worker = worker_update(world, worker_subset, idx, observed)
                if narrowed_worker == worker_subset:
                    continue
                child = dp(
                    controller_subset,
                    narrowed_worker,
                    used_mask | (1 << idx),
                    hidden_mask,
                )
                acq_cost = action["acquisition_cost"]
                exp_cost = action["exposure_cost"]
                candidate = (
                    acq_cost + exp_cost + child[0],
                    acq_cost + child[1],
                    exp_cost + child[2],
                    1.0 + child[3],
                )
                if (candidate[0], candidate[2]) < (best[0], best[2]):
                    best = candidate
                continue

            immediate_acq = action["acquisition_cost"]
            immediate_exp = action["exposure_cost"] if action["kind"] == "semantic" else 0.0
            total = immediate_acq + immediate_exp
            acq, exp, calls = immediate_acq, immediate_exp, 1.0
            next_used = used_mask | (1 << idx)
            next_hidden = hidden_mask | (1 << idx) if action["kind"] == "structured" else hidden_mask

            feasible = True
            for p, outcome, cstate in parts:
                wstate = worker_subset
                if action["kind"] == "semantic":
                    wstate = worker_update(world, worker_subset, idx, outcome)
                child = dp(cstate, wstate, next_used, next_hidden)
                if not math.isfinite(child[0]):
                    feasible = False
                    break
                total += p * child[0]
                acq += p * child[1]
                exp += p * child[2]
                calls += p * child[3]
            if not feasible:
                continue
            candidate = (total, acq, exp, calls)
            if (candidate[0], candidate[2]) < (best[0], best[2]):
                best = candidate

        return best

    initial = tuple(range(world.n))
    return dp(initial, initial, 0, 0)


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
    raw = [rng.gammavariate(rng.uniform(0.4, 2.0), 1.0) for _ in range(n)]
    z = sum(raw)
    priors = [x / z for x in raw]

    structured_p = {
        "balanced": 0.5,
        "structured_heavy": 0.8,
        "semantic_heavy": 0.2,
        "typed_index_then_semantic": 0.65,
    }[family]

    actions = []
    count = rng.randint(6, 8)
    for _ in range(count):
        kind = "structured" if rng.random() < structured_p else "semantic"
        outcomes = random_partition(rng, n, rng.choice([2, 3, 4]))
        acquisition = math.exp(rng.uniform(math.log(0.35), math.log(3.5)))
        exposure = math.exp(rng.uniform(math.log(1.8), math.log(13.0)))
        if kind == "structured":
            exposure *= rng.uniform(1.0, 1.5)
        actions.append({
            "kind": kind,
            "outcomes": outcomes,
            "acquisition_cost": acquisition,
            "exposure_cost": exposure,
        })

    if family == "typed_index_then_semantic":
        # Cheap typed indexes can narrow the controller cheaply, while semantic
        # exact evidence remains necessary to make the worker sufficient.
        coarse = [d % 2 for d in decisions]
        actions.append({
            "kind": "structured",
            "outcomes": tuple(coarse),
            "acquisition_cost": rng.uniform(0.2, 0.7),
            "exposure_cost": rng.uniform(5.0, 12.0),
        })

    # Semantic direct proof fallback ensures a worker-sufficient path always exists.
    actions.append({
        "kind": "semantic",
        "outcomes": tuple(decisions),
        "acquisition_cost": rng.uniform(1.5, 4.0),
        "exposure_cost": rng.uniform(2.5, 8.0),
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
        "p90": round(pct(0.90), 6),
    }


def main():
    rng = random.Random(SEED)
    families = ["balanced", "structured_heavy", "semantic_heavy", "typed_index_then_semantic"]

    coupled, decoupled = [], []
    coupled_exp, decoupled_exp = [], []
    coupled_acq, decoupled_acq = [], []
    coupled_calls, decoupled_calls = [], []
    by_family = defaultdict(lambda: {"total_ratio": [], "exposure_ratio": [], "call_ratio": []})

    for i in range(WORLDS):
        family = families[i % len(families)]
        world = gen_world(rng.randrange(1_000_000_000), family)
        c = coupled_exact(world)
        d = decoupled_exact(world)
        if not all(math.isfinite(x) for x in (*c, *d)):
            continue
        coupled.append(c[0]); decoupled.append(d[0])
        coupled_acq.append(c[1]); decoupled_acq.append(d[1])
        coupled_exp.append(c[2]); decoupled_exp.append(d[2])
        coupled_calls.append(c[3]); decoupled_calls.append(d[3])
        by_family[family]["total_ratio"].append(d[0] / c[0])
        by_family[family]["exposure_ratio"].append(d[2] / c[2] if c[2] > 0 else 1.0)
        by_family[family]["call_ratio"].append(d[3] / c[3] if c[3] > 0 else 1.0)

    result = {
        "experiment": "acquisition-exposure-separation-development-v0.2",
        "status": "development_only_corrected_state_model",
        "worlds_evaluated": len(coupled),
        "coupled": {
            "total_cost": summarize(coupled),
            "worker_exposure_cost": summarize(coupled_exp),
            "acquisition_cost": summarize(coupled_acq),
            "tool_calls": summarize(coupled_calls),
        },
        "decoupled": {
            "total_cost": summarize(decoupled),
            "worker_exposure_cost": summarize(decoupled_exp),
            "acquisition_cost": summarize(decoupled_acq),
            "tool_calls": summarize(decoupled_calls),
        },
        "mean_total_cost_reduction_pct": round(100.0 * (1.0 - statistics.mean(decoupled) / statistics.mean(coupled)), 3),
        "mean_worker_exposure_reduction_pct": round(100.0 * (1.0 - statistics.mean(decoupled_exp) / statistics.mean(coupled_exp)), 3),
        "mean_acquisition_cost_change_pct": round(100.0 * (statistics.mean(decoupled_acq) / statistics.mean(coupled_acq) - 1.0), 3),
        "mean_tool_call_change_pct": round(100.0 * (statistics.mean(decoupled_calls) / statistics.mean(coupled_calls) - 1.0), 3),
        "by_family": {
            family: {
                "mean_total_cost_reduction_pct": round(100.0 * (1.0 - statistics.mean(data["total_ratio"])), 3),
                "mean_worker_exposure_reduction_pct": round(100.0 * (1.0 - statistics.mean(data["exposure_ratio"])), 3),
                "mean_tool_call_change_pct": round(100.0 * (statistics.mean(data["call_ratio"]) - 1.0), 3),
            }
            for family, data in by_family.items()
        },
        "quality_invariant": "Termination requires both controller epistemic state and worker-visible epistemic state to be decision-sufficient. Hidden structured evidence must be selectively exposed or replaced by other exposed evidence before answer termination.",
        "claim_boundary": "Synthetic finite-decision mechanics. Controller-interpretability of structured outputs is contractual in the generator; real runtimes require typed adapters/validators. The discarded v0.1 benchmark did not separately track worker-visible state and must not be cited.",
    }
    print(json.dumps(result, indent=2))

    assert len(coupled) >= 180


if __name__ == "__main__":
    main()
