#!/usr/bin/env python3
from __future__ import annotations

import functools
import hashlib
import json
import math
import random
import statistics

import discover_context_acquisition_policy as acq
import discover_resolution_scheduler as res
import run_information_value_bench as info
import run_second_sealed_scheduler_test as sealed
import run_second_sealed_scheduler_test_fixed  # applies monotonic-cost invariant patch

PROTOCOL_FREEZE_COMMIT = "ee48bb6cea118f00fa5aba863deec6725c96d03f"
THIRD_SEALED_SEED = 3_118_771
SAMPLE_SEEDS = [3_118_777, 3_118_789]
SAMPLE_COUNTS = [2, 4, 8, 16]
BRANCH_SIGMAS = [0.5, 1.0, 1.5]
BASE_VALUE_SIGMA = 1.0
BASE_ACQ = acq.Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5)
BASE_RES = res.Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5, 0.0)


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


def stable_z(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def distorted(parts, sigma: float, *key: object):
    weights = []
    for idx, (p, state) in enumerate(parts):
        w = p * math.exp(sigma * stable_z(*key, idx) - 0.5 * sigma * sigma)
        weights.append((w, state))
    total = sum(w for w, _state in weights)
    return [(w / total, state) for w, state in weights]


def sample_states(parts, k: int, seed: int, *key: object):
    rng_seed = int.from_bytes(hashlib.sha256("|".join(map(str, (seed,) + key)).encode()).digest()[:8], "big")
    rng = random.Random(rng_seed)
    cumulative = []
    s = 0.0
    for p, state in parts:
        s += p
        cumulative.append((s, state))
    out = []
    for _ in range(k):
        u = rng.random()
        for c, state in cumulative:
            if u <= c:
                out.append(state)
                break
        else:
            out.append(cumulative[-1][1])
    return out


def acquisition_sampled_cost(inst: info.Instance, iid: int, k: int, branch_sigma: float, sample_seed: int) -> float:
    base_choose = acq.chooser(BASE_ACQ, iid, BASE_VALUE_SIGMA, sample_seed + 101)
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
            true_parts = info.partitions(inst, active, q)
            model_parts = distorted(true_parts, branch_sigma, "acq", iid, active, remaining, q, branch_sigma, sample_seed)
            samples = sample_states(model_parts, k, sample_seed, "acq", iid, active, remaining, q, k, branch_sigma)
            estimate = inst.queries[q].cost + statistics.fmean(base(st, nr) for st in samples)
            ranked.append((estimate, inst.queries[q].cost, q))
        _est, _cost, q = min(ranked)
        nr = tuple(x for x in remaining if x != q)
        return inst.queries[q].cost + sum(p * rollout(st, nr) for p, st in info.partitions(inst, active, q))

    return rollout(all_h, all_q)


def resolution_sampled_cost(ood: sealed.ResolutionOOD, iid: int, k: int, branch_sigma: float, sample_seed: int) -> float:
    world = ood.world
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def base(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = sealed.resolution_actions(ood, active, levels, False)
        if not acts:
            return math.inf
        sid, target = max(
            acts,
            key=lambda a: (
                res.policy_score(BASE_RES, world, active, levels, a[0], a[1], BASE_VALUE_SIGMA, sample_seed + 211, iid) *
                (res.incremental_cost(world, levels, a[0], a[1]) / sealed.action_cost(ood, levels, a[0], a[1])) ** BASE_RES.cost_exp,
                -sealed.action_cost(ood, levels, a[0], a[1]),
            ),
        )
        nl = list(levels); nl[sid] = target; nt = tuple(nl)
        return sealed.action_cost(ood, levels, sid, target) + sum(p * base(st, nt) for p, st in res.partitions(world, active, sid, target))

    @functools.lru_cache(maxsize=None)
    def rollout(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = sealed.resolution_actions(ood, active, levels, False)
        if not acts:
            return math.inf
        ranked = []
        for sid, target in acts:
            nl = list(levels); nl[sid] = target; nt = tuple(nl)
            true_parts = res.partitions(world, active, sid, target)
            model_parts = distorted(true_parts, branch_sigma, "res", iid, active, levels, sid, target, branch_sigma, sample_seed)
            samples = sample_states(model_parts, k, sample_seed, "res", iid, active, levels, sid, target, k, branch_sigma)
            estimate = sealed.action_cost(ood, levels, sid, target) + statistics.fmean(base(st, nt) for st in samples)
            ranked.append((estimate, sealed.action_cost(ood, levels, sid, target), sid, target))
        _est, _cost, sid, target = min(ranked)
        nl = list(levels); nl[sid] = target; nt = tuple(nl)
        return sealed.action_cost(ood, levels, sid, target) + sum(p * rollout(st, nt) for p, st in res.partitions(world, active, sid, target))

    return rollout(initial_active, initial_levels)


def main() -> None:
    # New seed after protocol freeze. Same broad OOD family definitions, entirely new worlds.
    acquisition = sealed.make_acquisition_worlds(THIRD_SEALED_SEED + 11, 14)  # 98 worlds
    resolution = sealed.make_resolution_worlds(THIRD_SEALED_SEED + 101, 14)   # 84 worlds

    acq_results = {}
    res_results = {}
    for branch_sigma in BRANCH_SIGMAS:
        for k in SAMPLE_COUNTS:
            a_vals = []
            r_vals = []
            for sample_seed in SAMPLE_SEEDS:
                for iid, inst, opt, _family in acquisition:
                    a_vals.append(acquisition_sampled_cost(inst, iid, k, branch_sigma, sample_seed) / opt)
                for iid, ood, opt, _family in resolution:
                    r_vals.append(resolution_sampled_cost(ood, iid, k, branch_sigma, sample_seed) / opt)
            key = f"sigma_{branch_sigma:.1f}_k_{k}"
            acq_results[key] = summarize(a_vals)
            res_results[key] = summarize(r_vals)

    # Strongest constrained comparator remains exact sequential-only DP, with no model error at all.
    sequential = [sealed.optimal_resolution_cost(ood, sequential=True) / opt for _iid, ood, opt, _family in resolution]

    result = {
        "experiment": "third-sealed-sampled-rollout-robustness-v0.1",
        "status": "sealed_after_protocol_freeze",
        "protocol_freeze_commit": PROTOCOL_FREEZE_COMMIT,
        "third_sealed_seed": THIRD_SEALED_SEED,
        "sample_seeds": SAMPLE_SEEDS,
        "sample_counts": SAMPLE_COUNTS,
        "branch_model_log_noise_sigmas": BRANCH_SIGMAS,
        "base_policy_value_noise_sigma": BASE_VALUE_SIGMA,
        "acquisition_worlds": len(acquisition),
        "resolution_worlds": len(resolution),
        "acquisition": acq_results,
        "resolution": res_results,
        "exact_sequential_only_oracle_resolution": summarize(sequential),
        "claim_boundary": "The sample counts, branch-model noise levels, and base-policy value noise were frozen before this world seed was introduced. Action selection uses only K Monte Carlo samples from deliberately perturbed branch probabilities; actual expected cost is evaluated under the true environment distribution. Synthetic controller mechanics only, not empirical LLM predictive calibration or end-to-end answer quality."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
