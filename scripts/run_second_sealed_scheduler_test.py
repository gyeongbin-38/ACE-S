#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import dataclass

import discover_context_acquisition_policy as acq
import discover_resolution_scheduler as res
import discover_retention_scheduler as ret
import run_information_value_bench as info

ROLLOUT_FREEZE_COMMIT = "79a3ea4c71377ba015079c46eef966709109bb82"
RETENTION_FREEZE_COMMIT = "773c314a0ec6b17bd28fc29ad435f65ae71dca26"
SEALED_SEED = 2_047_331
NOISE_SEEDS = [2_047_337, 2_047_351, 2_047_363]
SIGMAS = [0.0, 0.5, 1.0]

BASE_ACQ = acq.Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5)
BASE_RES = res.Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5, 0.0)
FROZEN_RETENTION = ret.Policy(1.0, 0.75, 1.5, 1.5, 1.0, 1.2)


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


# -------------------- Acquisition sealed worlds --------------------

def make_acquisition_instance(rng: random.Random, family: str) -> info.Instance:
    h = rng.randint(6, 9)
    d = rng.randint(2, min(4, h))
    decisions = [rng.randrange(d) for _ in range(h)]
    if len(set(decisions)) < 2:
        decisions = [i % d for i in range(h)]

    if family == "rare_branch":
        weights = [rng.random() ** 3 + 0.02 for _ in range(h)]
        weights[0] += 2.5
    else:
        weights = [rng.random() + 0.08 for _ in range(h)]
    s = sum(weights)
    prior = tuple(w / s for w in weights)

    queries: list[info.Query] = []
    qn = rng.randint(5, 8)
    for qi in range(qn):
        if family == "redundant_decoys" and qi < qn - 2:
            groups = rng.randint(1, 2)
            outcomes = tuple((i + qi) % groups if groups > 1 else 0 for i in range(h))
            cost = rng.uniform(0.05, 0.25)
        elif family == "binary_decisive" and qi == 0:
            outcomes = tuple(decisions)
            cost = rng.uniform(0.35, 0.9)
        elif family == "cost_reversal" and qi == 0:
            outcomes = tuple(decisions)
            cost = rng.uniform(3.0, 7.0)
        elif family == "cost_reversal" and qi in (1, 2):
            outcomes = tuple((decisions[i] + (i % 2)) % max(2, d) for i in range(h))
            cost = rng.uniform(0.12, 0.45)
        elif family == "hierarchical_clues":
            width = max(2, min(d, 2 + qi // 2))
            outcomes = tuple((decisions[i] * 3 + i) % width for i in range(h))
            cost = rng.uniform(0.12, 1.1) * (1.0 + 0.18 * qi)
        elif family == "anti_entropy":
            # High entropy reduction is not always the cheapest route to decision certainty.
            outcomes = tuple((i * (qi + 2) + (decisions[i] if qi % 3 == 0 else 0)) % rng.randint(2, max(3, h)) for i in range(h))
            cost = rng.uniform(0.08, 2.5) * (1.0 + (0.8 if qi % 3 == 0 else 0.0))
        else:  # mixed_unseen
            groups = rng.randint(2, h)
            outcomes = tuple((rng.randrange(groups) * d + decisions[i]) if rng.random() < 0.45 else rng.randrange(groups) for i in range(h))
            cost = math.exp(rng.uniform(math.log(0.08), math.log(5.5)))
        queries.append(info.Query(tuple(outcomes), round(cost, 6)))

    inst = info.Instance(tuple(decisions), prior, tuple(queries), family)
    return inst


def make_acquisition_worlds(seed: int, per_family: int = 30):
    rng = random.Random(seed)
    families = ["binary_decisive", "redundant_decoys", "rare_branch", "cost_reversal", "hierarchical_clues", "anti_entropy", "mixed_unseen"]
    worlds = []
    iid = 0
    for family in families:
        made = 0
        attempts = 0
        while made < per_family and attempts < per_family * 30:
            attempts += 1
            inst = make_acquisition_instance(rng, family)
            opt = info.optimal_cost(inst)
            if math.isfinite(opt) and opt > 0:
                worlds.append((iid, inst, opt, family))
                iid += 1
                made += 1
        if made != per_family:
            raise RuntimeError(f"could not build enough acquisition worlds for {family}: {made}")
    return worlds


def acquisition_costs(inst: info.Instance, iid: int, sigma: float, nseed: int):
    base_choose = acq.chooser(BASE_ACQ, iid, sigma, nseed)
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
            estimate = inst.queries[q].cost + sum(p * base(st, nr) for p, st in info.partitions(inst, active, q))
            ranked.append((estimate, inst.queries[q].cost, q))
        _est, _cost, q = min(ranked)
        nr = tuple(x for x in remaining if x != q)
        return inst.queries[q].cost + sum(p * rollout(st, nr) for p, st in info.partitions(inst, active, q))

    return base(all_h, all_q), rollout(all_h, all_q)


# -------------------- Resolution sealed worlds --------------------
@dataclass(frozen=True)
class ResolutionOOD:
    world: res.World
    call_overheads: tuple[float, ...]
    family: str


def action_cost(ood: ResolutionOOD, levels: tuple[int, ...], sid: int, target: int) -> float:
    return res.incremental_cost(ood.world, levels, sid, target) + ood.call_overheads[sid]


def make_resolution_ood(rng: random.Random, family: str) -> ResolutionOOD:
    base_family = "balanced"
    w = res.make_world(rng, base_family)
    sources = []
    overheads = []
    for src in w.sources:
        outcomes = list(src.outcomes)
        costs = list(src.cumulative_cost)
        if family == "dead_prefix":
            outcomes[0] = tuple(0 for _ in outcomes[0])
            outcomes[1] = tuple(0 for _ in outcomes[1])
            overhead = rng.uniform(0.35, 1.3)
        elif family == "call_dominated":
            costs = [c * rng.uniform(0.12, 0.3) for c in costs]
            # Keep cumulative monotonic after independent scaling.
            costs = [max(costs[i], costs[i - 1] + 0.02) if i else max(0.03, costs[i]) for i in range(4)]
            overhead = rng.uniform(0.8, 2.2)
        elif family == "ladder_friendly":
            overhead = rng.uniform(0.0, 0.03)
            costs = [costs[0] * 0.5, costs[1] * 0.6, costs[2] * 0.75, costs[3]]
            costs = [max(costs[i], costs[i - 1] + 0.01) if i else max(0.02, costs[i]) for i in range(4)]
        elif family == "raw_expensive":
            overhead = rng.uniform(0.05, 0.25)
            costs[3] += rng.uniform(3.0, 8.0)
        elif family == "late_bargain":
            overhead = rng.uniform(0.25, 0.9)
            # Payload cost grows only slightly after SUMMARY; repeated calls are the waste.
            c0 = rng.uniform(0.12, 0.35)
            costs = [c0, c0 + rng.uniform(0.05, 0.18), c0 + rng.uniform(0.12, 0.28), c0 + rng.uniform(0.2, 0.45)]
        else:  # mixed_economy
            overhead = rng.uniform(0.0, 1.4)
            scale = math.exp(rng.uniform(math.log(0.35), math.log(2.5)))
            costs = [c * scale for c in costs]
        sources.append(res.Source(tuple(outcomes), tuple(round(c, 6) for c in costs)))
        overheads.append(round(overhead, 6))
    world = res.World(w.decisions, w.prior, tuple(sources), family)
    return ResolutionOOD(world, tuple(overheads), family)


def make_resolution_worlds(seed: int, per_family: int = 24):
    rng = random.Random(seed)
    families = ["dead_prefix", "call_dominated", "ladder_friendly", "raw_expensive", "late_bargain", "mixed_economy"]
    worlds = []
    iid = 0
    for family in families:
        made = 0
        attempts = 0
        while made < per_family and attempts < per_family * 30:
            attempts += 1
            ood = make_resolution_ood(rng, family)
            opt = optimal_resolution_cost(ood, sequential=False)
            if math.isfinite(opt) and opt > 0:
                worlds.append((iid, ood, opt, family))
                iid += 1
                made += 1
        if made != per_family:
            raise RuntimeError(f"could not build enough resolution worlds for {family}: {made}")
    return worlds


def resolution_actions(ood: ResolutionOOD, active: tuple[int, ...], levels: tuple[int, ...], sequential: bool):
    world = ood.world
    out = []
    for sid in range(len(world.sources)):
        current = levels[sid]
        if current >= 4:
            continue
        targets = [current + 1] if sequential else range(current + 1, 5)
        for target in targets:
            # Sequential oracle may pay a zero-information prefix to unlock later fidelity.
            if sequential:
                future_useful = any(res.useful(world, active, sid, t) for t in range(target, 5))
                if future_useful:
                    out.append((sid, target))
            elif res.useful(world, active, sid, target):
                out.append((sid, target))
    return out


def optimal_resolution_cost(ood: ResolutionOOD, sequential: bool) -> float:
    world = ood.world
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = resolution_actions(ood, active, levels, sequential)
        if not acts:
            return math.inf
        best = math.inf
        for sid, target in acts:
            nl = list(levels)
            nl[sid] = target
            nt = tuple(nl)
            tail = sum(p * rec(st, nt) for p, st in res.partitions(world, active, sid, target))
            best = min(best, action_cost(ood, levels, sid, target) + tail)
        return best

    return rec(initial_active, initial_levels)


def resolution_base_and_rollout(ood: ResolutionOOD, iid: int, sigma: float, nseed: int):
    world = ood.world
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def base(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = resolution_actions(ood, active, levels, False)
        if not acts:
            return math.inf
        sid, target = max(
            acts,
            key=lambda a: (
                res.policy_score(BASE_RES, world, active, levels, a[0], a[1], sigma, nseed, iid) *
                (res.incremental_cost(world, levels, a[0], a[1]) / action_cost(ood, levels, a[0], a[1])) ** BASE_RES.cost_exp,
                -action_cost(ood, levels, a[0], a[1]),
            ),
        )
        nl = list(levels)
        nl[sid] = target
        nt = tuple(nl)
        return action_cost(ood, levels, sid, target) + sum(p * base(st, nt) for p, st in res.partitions(world, active, sid, target))

    @functools.lru_cache(maxsize=None)
    def rollout(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if res.solved(world, active):
            return 0.0
        acts = resolution_actions(ood, active, levels, False)
        if not acts:
            return math.inf
        ranked = []
        for sid, target in acts:
            nl = list(levels)
            nl[sid] = target
            nt = tuple(nl)
            estimate = action_cost(ood, levels, sid, target) + sum(p * base(st, nt) for p, st in res.partitions(world, active, sid, target))
            ranked.append((estimate, action_cost(ood, levels, sid, target), sid, target))
        _est, _cost, sid, target = min(ranked)
        nl = list(levels)
        nl[sid] = target
        nt = tuple(nl)
        return action_cost(ood, levels, sid, target) + sum(p * rollout(st, nt) for p, st in res.partitions(world, active, sid, target))

    return base(initial_active, initial_levels), rollout(initial_active, initial_levels)


# -------------------- Retention sealed worlds --------------------

def make_retention_ood(rng: random.Random, family: str) -> ret.Item:
    horizon = rng.randint(6, 12)
    if family == "periodic_reuse":
        p_need = [0.72 if t % 3 == 0 else 0.06 for t in range(horizon)]
        p_exact = [rng.uniform(0.2, 0.55) for _ in range(horizon)]
    elif family == "delayed_spike":
        spike = rng.randint(horizon // 2, horizon - 1)
        p_need = [rng.uniform(0.02, 0.08) if t < spike else rng.uniform(0.55, 0.9) for t in range(horizon)]
        p_exact = [rng.uniform(0.25, 0.7) for _ in range(horizon)]
    elif family == "exactness_switch":
        p_need = [rng.uniform(0.2, 0.55) for _ in range(horizon)]
        p_exact = [rng.uniform(0.05, 0.2) if t < horizon // 2 else rng.uniform(0.8, 0.97) for t in range(horizon)]
    elif family == "bimodal_need":
        p_need = [rng.uniform(0.55, 0.85) if t < 2 or t >= horizon - 2 else rng.uniform(0.02, 0.1) for t in range(horizon)]
        p_exact = [rng.uniform(0.15, 0.65) for _ in range(horizon)]
    elif family == "compaction_expensive":
        p_need = [rng.uniform(0.1, 0.4) for _ in range(horizon)]
        p_exact = [rng.uniform(0.1, 0.45) for _ in range(horizon)]
    elif family == "raw_residency_expensive":
        p_need = [rng.uniform(0.08, 0.32) for _ in range(horizon)]
        p_exact = [rng.uniform(0.05, 0.35) for _ in range(horizon)]
    else:  # high_abstraction_risk
        p_need = [rng.uniform(0.15, 0.55) for _ in range(horizon)]
        p_exact = [rng.uniform(0.2, 0.65) for _ in range(horizon)]

    reacquire = rng.uniform(2.0, 10.0)
    raw_hold = rng.uniform(0.15, 0.8)
    abstract_hold = raw_hold * rng.uniform(0.06, 0.25)
    compact = rng.uniform(0.1, 1.0)
    failure = rng.uniform(0.04, 0.22)
    if family == "compaction_expensive":
        compact = rng.uniform(2.5, 7.0)
    if family == "raw_residency_expensive":
        raw_hold = rng.uniform(1.0, 2.8)
    if family == "high_abstraction_risk":
        failure = rng.uniform(0.5, 0.85)
    return ret.Item(tuple(p_need), tuple(p_exact), raw_hold, abstract_hold, reacquire, compact, failure, family)


def make_retention_worlds(seed: int, per_family: int = 40):
    rng = random.Random(seed)
    families = ["periodic_reuse", "delayed_spike", "exactness_switch", "bimodal_need", "compaction_expensive", "raw_residency_expensive", "high_abstraction_risk"]
    out = []
    iid = 0
    for family in families:
        for _ in range(per_family):
            item = make_retention_ood(rng, family)
            out.append((iid, item, ret.optimal_cost(item), family))
            iid += 1
    return out


def main() -> None:
    # Acquisition: 210 new worlds × 3 sigmas × 3 noise seeds.
    acquisition = make_acquisition_worlds(SEALED_SEED + 11, 30)
    acq_base, acq_rollout = [], []
    acq_family: dict[str, dict[str, list[float]]] = {}
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, inst, opt, family in acquisition:
                b, r = acquisition_costs(inst, iid, sigma, nseed)
                acq_base.append(b / opt)
                acq_rollout.append(r / opt)
                row = acq_family.setdefault(family, {"base": [], "rollout": []})
                row["base"].append(b / opt)
                row["rollout"].append(r / opt)

    # Resolution: 144 new OOD worlds × 3 sigmas × 3 noise seeds.
    resolution = make_resolution_worlds(SEALED_SEED + 101, 24)
    res_base, res_rollout, res_seq = [], [], []
    res_family: dict[str, dict[str, list[float]]] = {}
    for iid, ood, opt, family in resolution:
        sequential_opt = optimal_resolution_cost(ood, sequential=True)
        res_seq.append(sequential_opt / opt)
        row = res_family.setdefault(family, {"base": [], "rollout": [], "sequential_oracle": []})
        row["sequential_oracle"].append(sequential_opt / opt)
        for sigma in SIGMAS:
            for nseed in NOISE_SEEDS:
                b, r = resolution_base_and_rollout(ood, iid, sigma, nseed)
                res_base.append(b / opt)
                res_rollout.append(r / opt)
                row["base"].append(b / opt)
                row["rollout"].append(r / opt)

    # Retention: 280 new OOD lifecycle items × 3 sigmas × 3 noise seeds.
    retention = make_retention_worlds(SEALED_SEED + 1001, 40)
    ret_frozen = []
    ret_raw, ret_abstract, ret_drop = [], [], []
    ret_family: dict[str, dict[str, list[float]]] = {}
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in retention:
                c = ret.heuristic_cost(item, FROZEN_RETENTION, sigma, nseed, iid)
                ret_frozen.append(c / opt)
                row = ret_family.setdefault(family, {"frozen": [], "raw": [], "abstract": [], "drop": []})
                row["frozen"].append(c / opt)
                # Static baselines are deterministic; repeated here only for weighting parity in family comparisons.
                raw = ret.baseline_cost(item, ret.RAW) / opt
                abstract = ret.baseline_cost(item, ret.ABSTRACT) / opt
                drop = ret.baseline_cost(item, ret.DROP) / opt
                ret_raw.append(raw); ret_abstract.append(abstract); ret_drop.append(drop)
                row["raw"].append(raw); row["abstract"].append(abstract); row["drop"].append(drop)

    result = {
        "experiment": "second-sealed-context-scheduler-ood-v0.1",
        "status": "sealed_after_freeze",
        "rollout_freeze_commit": ROLLOUT_FREEZE_COMMIT,
        "retention_freeze_commit": RETENTION_FREEZE_COMMIT,
        "sealed_seed": SEALED_SEED,
        "noise_seeds": NOISE_SEEDS,
        "sigmas": SIGMAS,
        "acquisition": {
            "worlds": len(acquisition),
            "evaluations": len(acq_rollout),
            "base": summarize(acq_base),
            "rollout": summarize(acq_rollout),
            "mean_cost_reduction_vs_base_pct": round(100 * (1 - statistics.fmean(acq_rollout) / statistics.fmean(acq_base)), 2),
            "rollout_beats_or_ties_base_rate": round(100 * sum(r <= b + 1e-12 for r, b in zip(acq_rollout, acq_base)) / len(acq_rollout), 2),
            "by_family": {k: {name: summarize(vals) for name, vals in v.items()} for k, v in acq_family.items()},
        },
        "resolution": {
            "worlds": len(resolution),
            "evaluations": len(res_rollout),
            "base": summarize(res_base),
            "rollout": summarize(res_rollout),
            "exact_sequential_only_oracle": summarize(res_seq),
            "mean_cost_reduction_vs_base_pct": round(100 * (1 - statistics.fmean(res_rollout) / statistics.fmean(res_base)), 2),
            "rollout_beats_or_ties_base_rate": round(100 * sum(r <= b + 1e-12 for r, b in zip(res_rollout, res_base)) / len(res_rollout), 2),
            "rollout_mean_advantage_vs_sequential_oracle_pct": round(100 * (1 - statistics.fmean(res_rollout) / statistics.fmean(res_seq)), 2),
            "by_family": {k: {name: summarize(vals) for name, vals in v.items()} for k, v in res_family.items()},
        },
        "retention": {
            "items": len(retention),
            "evaluations": len(ret_frozen),
            "frozen": summarize(ret_frozen),
            "keep_raw": summarize(ret_raw),
            "keep_abstract": summarize(ret_abstract),
            "drop": summarize(ret_drop),
            "mean_cost_reduction_vs_keep_raw_pct": round(100 * (1 - statistics.fmean(ret_frozen) / statistics.fmean(ret_raw)), 2),
            "by_family": {k: {name: summarize(vals) for name, vals in v.items()} for k, v in ret_family.items()},
        },
        "claim_boundary": "All policies and rollout rules were frozen before this seed and these OOD generators were introduced. Synthetic controller mechanics only: acquisition/resolution continue to synthetic decision certainty, retention reacquires exact evidence when required. Rollout has access to finite-world transition probabilities; a real agent must approximate them. This is not natural-language routing or end-to-end LLM answer-quality evidence.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
