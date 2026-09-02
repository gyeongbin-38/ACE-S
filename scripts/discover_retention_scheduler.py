#!/usr/bin/env python3
from __future__ import annotations

import functools
import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

TRAIN_SEED = 441_101
VALIDATION_SEED = 441_121
TRAIN_ITEMS = 80
VALIDATION_ITEMS = 160
NOISE_SEEDS = [881_003, 881_021]
SIGMAS = [0.0, 0.25, 0.5, 1.0]

RAW = "RAW"
ABSTRACT = "ABSTRACT"
DROP = "DROP"


@dataclass(frozen=True)
class Item:
    p_need: tuple[float, ...]
    p_exact: tuple[float, ...]  # conditional on need
    raw_hold: float
    abstract_hold: float
    reacquire_cost: float
    compact_cost: float
    abstract_failure: float
    family: str


@dataclass(frozen=True)
class Policy:
    benefit_exp: float
    cost_exp: float
    exact_weight: float
    abstract_risk_weight: float
    discount: float
    threshold: float


def zscore(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def noisy_prob(p: float, sigma: float, seed: int, *key: object) -> float:
    if sigma <= 0.0:
        return p
    # Noise odds rather than raw probability to keep estimates in [0,1].
    p = min(1 - 1e-6, max(1e-6, p))
    logit = math.log(p / (1 - p))
    return 1.0 / (1.0 + math.exp(-(logit + sigma * zscore(seed, *key))))


def future_stats(item: Item, start: int, policy: Policy, sigma: float, nseed: int, iid: int):
    need = 0.0
    exact = 0.0
    semantic = 0.0
    survival = 1.0
    for t in range(start, len(item.p_need)):
        d = policy.discount ** (t - start)
        pn = noisy_prob(item.p_need[t], sigma, nseed, iid, t, "need")
        pe = noisy_prob(item.p_exact[t], sigma, nseed, iid, t, "exact")
        need += d * pn
        exact += d * pn * pe
        semantic += d * pn * (1.0 - pe)
        survival *= (1.0 - pn)
    return need, exact, semantic, survival


def policy_choice(item: Item, start: int, available: str, policy: Policy, sigma: float, nseed: int, iid: int) -> str:
    if start >= len(item.p_need):
        return DROP
    need, exact, semantic, _survival = future_stats(item, start, policy, sigma, nseed, iid)
    remaining = len(item.p_need) - start
    raw_benefit = (need + policy.exact_weight * exact) * item.reacquire_cost
    abstract_effective_semantic = semantic * max(0.0, 1.0 - policy.abstract_risk_weight * item.abstract_failure)
    abstract_benefit = abstract_effective_semantic * item.reacquire_cost
    raw_cost = item.raw_hold * remaining
    abstract_cost = item.abstract_hold * remaining + (item.compact_cost if available == RAW else 0.0)

    def ratio(benefit: float, cost: float) -> float:
        return (max(benefit, 1e-12) ** policy.benefit_exp) / (max(cost, 1e-12) ** policy.cost_exp)

    candidates = [(DROP, policy.threshold)]
    if available == RAW:
        candidates.append((RAW, ratio(raw_benefit, raw_cost)))
        candidates.append((ABSTRACT, ratio(abstract_benefit, abstract_cost)))
    elif available == ABSTRACT:
        candidates.append((ABSTRACT, ratio(abstract_benefit, abstract_cost)))
    return max(candidates, key=lambda x: (x[1], {DROP: 0, ABSTRACT: 1, RAW: 2}[x[0]]))[0]


def heuristic_cost(item: Item, policy: Policy, sigma: float, nseed: int, iid: int) -> float:
    initial = policy_choice(item, 0, RAW, policy, sigma, nseed, iid)
    initial_transition = item.compact_cost if initial == ABSTRACT else 0.0

    @functools.lru_cache(maxsize=None)
    def rec(t: int, mode: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        hold = item.raw_hold if mode == RAW else item.abstract_hold if mode == ABSTRACT else 0.0
        pn = item.p_need[t]
        pe = item.p_exact[t]

        def after(available: str, transition_extra: float = 0.0) -> float:
            if t + 1 >= len(item.p_need):
                return transition_extra
            nxt = policy_choice(item, t + 1, available, policy, sigma, nseed, iid)
            trans = transition_extra
            if available == RAW and nxt == ABSTRACT:
                trans += item.compact_cost
            return trans + rec(t + 1, nxt)

        # No future need this step.
        no_need_available = mode
        no_need = after(no_need_available)

        # Need occurs. Exact or failed abstract forces RAW reacquisition if RAW is not resident.
        if mode == RAW:
            need_cost = after(RAW)
        elif mode == DROP:
            need_cost = item.reacquire_cost + after(RAW)
        else:
            exact_branch = item.reacquire_cost + after(RAW)
            semantic_success = after(ABSTRACT)
            semantic_fail = item.reacquire_cost + after(RAW)
            semantic_branch = (1.0 - item.abstract_failure) * semantic_success + item.abstract_failure * semantic_fail
            need_cost = pe * exact_branch + (1.0 - pe) * semantic_branch
        return hold + (1.0 - pn) * no_need + pn * need_cost

    return initial_transition + rec(0, initial)


def optimal_cost(item: Item) -> float:
    @functools.lru_cache(maxsize=None)
    def rec(t: int, mode: str) -> float:
        if t >= len(item.p_need):
            return 0.0
        hold = item.raw_hold if mode == RAW else item.abstract_hold if mode == ABSTRACT else 0.0
        pn = item.p_need[t]
        pe = item.p_exact[t]

        def best_after(available: str) -> float:
            if t + 1 >= len(item.p_need):
                return 0.0
            modes = [DROP]
            if available == RAW:
                modes += [RAW, ABSTRACT]
            elif available == ABSTRACT:
                modes += [ABSTRACT]
            best = math.inf
            for nxt in modes:
                transition = item.compact_cost if available == RAW and nxt == ABSTRACT else 0.0
                best = min(best, transition + rec(t + 1, nxt))
            return best

        no_need = best_after(mode)
        if mode == RAW:
            need_cost = best_after(RAW)
        elif mode == DROP:
            need_cost = item.reacquire_cost + best_after(RAW)
        else:
            exact_branch = item.reacquire_cost + best_after(RAW)
            semantic_success = best_after(ABSTRACT)
            semantic_fail = item.reacquire_cost + best_after(RAW)
            need_cost = pe * exact_branch + (1.0 - pe) * ((1.0 - item.abstract_failure) * semantic_success + item.abstract_failure * semantic_fail)
        return hold + (1.0 - pn) * no_need + pn * need_cost

    # Raw is available immediately after the current task, before future horizon begins.
    return min(
        rec(0, DROP),
        rec(0, RAW),
        item.compact_cost + rec(0, ABSTRACT),
    )


def baseline_cost(item: Item, mode: str) -> float:
    if mode == RAW:
        return item.raw_hold * len(item.p_need)
    if mode == ABSTRACT:
        hold = item.abstract_hold * len(item.p_need) + item.compact_cost
        expected_reacq = 0.0
        for pn, pe in zip(item.p_need, item.p_exact):
            expected_reacq += pn * (pe + (1.0 - pe) * item.abstract_failure) * item.reacquire_cost
        return hold + expected_reacq
    return sum(item.p_need) * item.reacquire_cost


def make_item(rng: random.Random, family: str) -> Item:
    horizon = rng.randint(4, 9)
    if family == "bursty":
        pivot = rng.randrange(horizon)
        p_need = [min(0.95, 0.08 + 0.75 * math.exp(-abs(t - pivot) / 1.2)) for t in range(horizon)]
    elif family == "sparse":
        p_need = [rng.uniform(0.03, 0.18) for _ in range(horizon)]
    else:
        base = rng.uniform(0.12, 0.55)
        p_need = [min(0.9, max(0.03, base * rng.uniform(0.65, 1.35))) for _ in range(horizon)]
    if family == "exact_heavy":
        p_exact = [rng.uniform(0.65, 0.95) for _ in range(horizon)]
    elif family == "semantic_heavy":
        p_exact = [rng.uniform(0.05, 0.3) for _ in range(horizon)]
    else:
        p_exact = [rng.uniform(0.15, 0.75) for _ in range(horizon)]
    reacquire = rng.uniform(2.0, 8.0)
    if family == "high_reacquire":
        reacquire *= 2.5
    elif family == "low_reacquire":
        reacquire *= 0.45
    raw_hold = rng.uniform(0.18, 0.75)
    abstract_hold = raw_hold * rng.uniform(0.08, 0.28)
    compact = rng.uniform(0.15, 1.2)
    abstract_failure = rng.uniform(0.03, 0.22)
    if family == "summary_risky":
        abstract_failure = rng.uniform(0.3, 0.65)
    return Item(tuple(p_need), tuple(p_exact), raw_hold, abstract_hold, reacquire, compact, abstract_failure, family)


def make_items(seed: int, n: int):
    rng = random.Random(seed)
    families = ["balanced", "bursty", "sparse", "exact_heavy", "semantic_heavy", "high_reacquire", "low_reacquire", "summary_risky"]
    items = []
    for i in range(n):
        family = families[i % len(families)]
        item = make_item(rng, family)
        opt = optimal_cost(item)
        items.append((i, item, opt))
    return items


def candidate_space():
    rng = random.Random(772_331)
    axes = {
        "benefit_exp": [0.35, 0.5, 0.75, 1.0],
        "cost_exp": [0.75, 1.0, 1.25, 1.5],
        "exact_weight": [0.0, 0.5, 1.0, 1.5],
        "abstract_risk_weight": [0.5, 1.0, 1.5, 2.0],
        "discount": [0.65, 0.8, 0.9, 1.0],
        "threshold": [0.65, 0.85, 1.0, 1.2, 1.5],
    }
    seen = set()
    while len(seen) < 320:
        seen.add(Policy(*(rng.choice(axes[k]) for k in axes)))
    return list(seen)


def evaluate(policy: Policy, items, sigmas, seeds):
    ratios = []
    for sigma in sigmas:
        for nseed in seeds:
            for iid, item, opt in items:
                ratios.append(heuristic_cost(item, policy, sigma, nseed, iid) / opt)
    return ratios


def summarize(vals):
    v = sorted(vals)
    return {"mean": round(statistics.fmean(v), 5), "median": round(statistics.median(v), 5), "p90": round(v[int(0.9 * (len(v)-1))], 5), "within_10pct": round(100 * sum(x <= 1.1 + 1e-12 for x in v) / len(v), 2), "within_25pct": round(100 * sum(x <= 1.25 + 1e-12 for x in v) / len(v), 2)}


def main():
    train = make_items(TRAIN_SEED, TRAIN_ITEMS)
    validation = make_items(VALIDATION_SEED, VALIDATION_ITEMS)
    stage1 = []
    for p in candidate_space():
        vals = evaluate(p, train, [0.0, 0.5, 1.0], [NOISE_SEEDS[0]])
        s = summarize(vals)
        obj = s["mean"] + 0.25 * max(0.0, s["p90"] - 1.0)
        stage1.append((obj, p))
    stage1.sort(key=lambda x: x[0])
    stage2 = []
    for _obj, p in stage1[:24]:
        vals = evaluate(p, validation, SIGMAS, NOISE_SEEDS)
        s = summarize(vals)
        obj = s["mean"] + 0.25 * max(0.0, s["p90"] - 1.0)
        stage2.append((obj, p, s))
    stage2.sort(key=lambda x: x[0])
    winner = stage2[0]
    baselines = {}
    for mode in [RAW, ABSTRACT, DROP]:
        ratios = [baseline_cost(item, mode) / opt for _iid, item, opt in validation]
        baselines[mode.lower()] = summarize(ratios)
    result = {
        "experiment": "lifecycle-retention-scheduler-search-v0.1",
        "status": "development_search_only",
        "candidate_count": 320,
        "train_items": len(train),
        "validation_items": len(validation),
        "selected_policy": asdict(winner[1]),
        "selected_validation": winner[2],
        "baselines": baselines,
        "top_candidates": [{"policy": asdict(p), "summary": s, "objective": round(o, 6)} for o, p, s in stage2[:5]],
        "guardrail": "Development-only retention search. Freeze before unseen lifecycle seeds/families are introduced.",
        "caveat": "Synthetic lifecycle mechanics benchmark. It measures expected residency, compaction, and reacquisition cost under equal task correctness; it is not an end-to-end LLM quality benchmark."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
