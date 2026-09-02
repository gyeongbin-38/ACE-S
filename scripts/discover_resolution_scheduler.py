#!/usr/bin/env python3
from __future__ import annotations

import functools
import hashlib
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass

TRAIN_SEED = 930_211
VALIDATION_SEED = 930_223
NOISE_SEEDS = [711_019, 711_029]
TRAIN_WORLDS = 48
VALIDATION_WORLDS = 96
SIGMAS = [0.0, 0.25, 0.5, 1.0]
LEVELS = (1, 2, 3, 4)  # INDEX, SUMMARY, EXTRACT, RAW


@dataclass(frozen=True)
class Source:
    outcomes: tuple[tuple[int, ...], ...]  # level-1 indexed outcomes
    cumulative_cost: tuple[float, float, float, float]


@dataclass(frozen=True)
class World:
    decisions: tuple[int, ...]
    prior: tuple[float, ...]
    sources: tuple[Source, ...]
    family: str


@dataclass(frozen=True)
class Policy:
    ig_exp: float
    cost_exp: float
    gini_weight: float
    solve_weight: float
    worst_weight: float
    count_weight: float
    span_weight: float


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0)


def decision_mass(world: World, active: tuple[int, ...]) -> dict[int, float]:
    total = sum(world.prior[h] for h in active)
    mass: dict[int, float] = {}
    for h in active:
        d = world.decisions[h]
        mass[d] = mass.get(d, 0.0) + world.prior[h] / total
    return mass


def decision_entropy(world: World, active: tuple[int, ...]) -> float:
    return entropy(list(decision_mass(world, active).values()))


def gini(world: World, active: tuple[int, ...]) -> float:
    return 1.0 - sum(p * p for p in decision_mass(world, active).values())


def solved(world: World, active: tuple[int, ...]) -> bool:
    return len({world.decisions[h] for h in active}) <= 1


def partitions(world: World, active: tuple[int, ...], source_id: int, level: int):
    labels = world.sources[source_id].outcomes[level - 1]
    buckets: dict[int, list[int]] = {}
    for h in active:
        buckets.setdefault(labels[h], []).append(h)
    total = sum(world.prior[h] for h in active)
    out = []
    for hs in buckets.values():
        state = tuple(hs)
        prob = sum(world.prior[h] for h in state) / total
        out.append((prob, state))
    return out


def info_gain(world: World, active: tuple[int, ...], sid: int, level: int) -> float:
    before = decision_entropy(world, active)
    after = sum(p * decision_entropy(world, st) for p, st in partitions(world, active, sid, level))
    return max(0.0, before - after)


def gini_gain(world: World, active: tuple[int, ...], sid: int, level: int) -> float:
    before = gini(world, active)
    after = sum(p * gini(world, st) for p, st in partitions(world, active, sid, level))
    return max(0.0, before - after)


def solve_probability(world: World, active: tuple[int, ...], sid: int, level: int) -> float:
    return sum(p for p, st in partitions(world, active, sid, level) if solved(world, st))


def worst_gain(world: World, active: tuple[int, ...], sid: int, level: int) -> float:
    before = decision_entropy(world, active)
    worst_after = max(decision_entropy(world, st) for _p, st in partitions(world, active, sid, level))
    return max(0.0, before - worst_after)


def count_gain(world: World, active: tuple[int, ...], sid: int, level: int) -> float:
    before = len({world.decisions[h] for h in active})
    if before <= 1:
        return 0.0
    after = sum(p * len({world.decisions[h] for h in st}) for p, st in partitions(world, active, sid, level))
    return max(0.0, before - after) / (before - 1)


def incremental_cost(world: World, levels: tuple[int, ...], sid: int, target: int) -> float:
    prev = levels[sid]
    costs = world.sources[sid].cumulative_cost
    before = 0.0 if prev == 0 else costs[prev - 1]
    return costs[target - 1] - before


def useful(world: World, active: tuple[int, ...], sid: int, level: int) -> bool:
    return info_gain(world, active, sid, level) > 1e-12


def zscore(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def noisy(v: float, sigma: float, seed: int, *key: object) -> float:
    if sigma <= 0.0 or v <= 0.0:
        return v
    z = zscore(seed, sigma, *key)
    return v * math.exp(sigma * z - 0.5 * sigma * sigma)


def policy_score(policy: Policy, world: World, active: tuple[int, ...], levels: tuple[int, ...], sid: int, target: int, sigma: float, nseed: int, iid: int) -> float:
    key = (iid, active, levels, sid, target)
    ig = noisy(info_gain(world, active, sid, target), sigma, nseed, *key, "ig")
    gg = noisy(gini_gain(world, active, sid, target), sigma, nseed, *key, "gini")
    sp = min(1.0, noisy(solve_probability(world, active, sid, target), sigma, nseed, *key, "solve"))
    wg = noisy(worst_gain(world, active, sid, target), sigma, nseed, *key, "worst")
    cg = noisy(count_gain(world, active, sid, target), sigma, nseed, *key, "count")
    span = target - levels[sid]
    value = (ig ** policy.ig_exp + policy.gini_weight * gg + policy.solve_weight * sp + policy.worst_weight * wg + policy.count_weight * cg)
    value *= 1.0 + policy.span_weight * max(0, span - 1)
    cost = incremental_cost(world, levels, sid, target)
    return value / (cost ** policy.cost_exp)


def expected_cost(world: World, chooser, jump_allowed: bool = True) -> float:
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if solved(world, active):
            return 0.0
        actions = []
        for sid in range(len(world.sources)):
            current = levels[sid]
            targets = range(current + 1, 5) if jump_allowed else ([current + 1] if current < 4 else [])
            for target in targets:
                if useful(world, active, sid, target):
                    actions.append((sid, target))
        if not actions:
            return math.inf
        sid, target = chooser(world, active, levels, actions)
        new_levels = list(levels)
        new_levels[sid] = target
        nl = tuple(new_levels)
        tail = sum(p * rec(st, nl) for p, st in partitions(world, active, sid, target))
        return incremental_cost(world, levels, sid, target) + tail

    return rec(initial_active, initial_levels)


def optimal_cost(world: World) -> float:
    initial_active = tuple(range(len(world.decisions)))
    initial_levels = tuple(0 for _ in world.sources)

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], levels: tuple[int, ...]) -> float:
        if solved(world, active):
            return 0.0
        best = math.inf
        for sid in range(len(world.sources)):
            for target in range(levels[sid] + 1, 5):
                if not useful(world, active, sid, target):
                    continue
                nl = list(levels)
                nl[sid] = target
                nt = tuple(nl)
                tail = sum(p * rec(st, nt) for p, st in partitions(world, active, sid, target))
                best = min(best, incremental_cost(world, levels, sid, target) + tail)
        return best

    return rec(initial_active, initial_levels)


def chooser_for(policy: Policy, sigma: float, nseed: int, iid: int):
    def choose(world, active, levels, actions):
        return max(actions, key=lambda a: (policy_score(policy, world, active, levels, a[0], a[1], sigma, nseed, iid), -incremental_cost(world, levels, a[0], a[1]), -a[1], -a[0]))
    return choose


def ladder_chooser(world, active, levels, actions):
    # Only next-level actions are exposed by expected_cost(jump_allowed=False).
    return max(actions, key=lambda a: (info_gain(world, active, a[0], a[1]) / incremental_cost(world, levels, a[0], a[1]), -incremental_cost(world, levels, a[0], a[1])))


def coarsen(raw: list[int], groups: int) -> tuple[int, ...]:
    return tuple(x % max(1, groups) for x in raw)


def make_world(rng: random.Random, family: str) -> World:
    h = rng.randint(5, 8)
    d = rng.randint(2, min(4, h))
    decisions = tuple(rng.randrange(d) for _ in range(h))
    if len(set(decisions)) < 2:
        decisions = tuple(i % d for i in range(h))
    weights = [rng.random() ** (2.0 if family == "prior_skew" else 1.0) + 0.05 for _ in range(h)]
    total = sum(weights)
    prior = tuple(w / total for w in weights)
    sources = []
    for _ in range(rng.randint(3, 5)):
        raw_groups = rng.randint(3, h)
        raw = [rng.randrange(raw_groups) for _ in range(h)]
        # Ensure some decision relevance.
        if rng.random() < 0.55:
            raw = [raw[i] * d + decisions[i] for i in range(h)]
        extract_groups = max(2, raw_groups - rng.randint(0, 2))
        summary_groups = max(2, extract_groups - rng.randint(0, 2))
        index_groups = max(1, summary_groups - rng.randint(0, 2))
        outcomes = (coarsen(raw, index_groups), coarsen(raw, summary_groups), coarsen(raw, extract_groups), tuple(raw))
        base = rng.uniform(0.12, 0.4)
        if family == "raw_bargain":
            steps = [base, rng.uniform(0.1, 0.3), rng.uniform(0.15, 0.5), rng.uniform(0.15, 0.7)]
        elif family == "expensive_raw":
            steps = [base, rng.uniform(0.2, 0.6), rng.uniform(0.5, 1.4), rng.uniform(2.5, 6.0)]
        elif family == "weak_low_levels":
            steps = [base, rng.uniform(0.2, 0.5), rng.uniform(0.4, 1.0), rng.uniform(0.8, 2.0)]
            outcomes = (tuple(0 for _ in raw), coarsen(raw, 2), coarsen(raw, max(2, extract_groups)), tuple(raw))
        else:
            steps = [base, rng.uniform(0.15, 0.5), rng.uniform(0.35, 1.1), rng.uniform(0.7, 2.8)]
        cumulative = []
        s = 0.0
        for step in steps:
            s += step
            cumulative.append(round(s, 6))
        sources.append(Source(outcomes=outcomes, cumulative_cost=tuple(cumulative)))
    return World(decisions=decisions, prior=prior, sources=tuple(sources), family=family)


def make_worlds(seed: int, n: int):
    rng = random.Random(seed)
    families = ["balanced", "raw_bargain", "expensive_raw", "weak_low_levels", "prior_skew"]
    worlds = []
    while len(worlds) < n:
        family = families[len(worlds) % len(families)]
        w = make_world(rng, family)
        opt = optimal_cost(w)
        if math.isfinite(opt) and opt > 0:
            worlds.append((len(worlds), w, opt))
    return worlds


def candidate_space() -> list[Policy]:
    rng = random.Random(199_331)
    axes = {
        "ig_exp": [0.2, 0.35, 0.5, 0.75, 1.0],
        "cost_exp": [0.8, 1.0, 1.25, 1.5],
        "gini_weight": [0.0, 0.5, 1.0],
        "solve_weight": [0.0, 0.75, 1.5, 2.5],
        "worst_weight": [0.0, 0.5, 1.0],
        "count_weight": [0.0, 0.5, 1.0],
        "span_weight": [-0.15, 0.0, 0.15, 0.35],
    }
    seen = {Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5, 0.0), Policy(1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)}
    while len(seen) < 256:
        seen.add(Policy(*(rng.choice(axes[k]) for k in axes)))
    return list(seen)


def evaluate(policy: Policy, worlds, sigmas, noise_seeds):
    ratios = []
    for sigma in sigmas:
        for seed in noise_seeds:
            for iid, world, opt in worlds:
                c = expected_cost(world, chooser_for(policy, sigma, seed, iid), jump_allowed=True)
                ratios.append(c / opt)
    return ratios


def summarize(values: list[float]):
    v = sorted(values)
    return {"mean": round(statistics.fmean(v), 5), "median": round(statistics.median(v), 5), "p90": round(v[int(0.9 * (len(v)-1))], 5), "within_10pct": round(100 * sum(x <= 1.1 + 1e-12 for x in v) / len(v), 2)}


def main():
    train = make_worlds(TRAIN_SEED, TRAIN_WORLDS)
    validation = make_worlds(VALIDATION_SEED, VALIDATION_WORLDS)
    candidates = candidate_space()
    stage1 = []
    for p in candidates:
        vals = evaluate(p, train, [0.0, 0.5, 1.0], [NOISE_SEEDS[0]])
        s = summarize(vals)
        obj = s["mean"] + 0.3 * max(0.0, s["p90"] - 1.0)
        stage1.append((obj, p))
    stage1.sort(key=lambda x: x[0])
    stage2 = []
    for _obj, p in stage1[:20]:
        vals = evaluate(p, validation, SIGMAS, NOISE_SEEDS)
        s = summarize(vals)
        obj = s["mean"] + 0.3 * max(0.0, s["p90"] - 1.0)
        stage2.append((obj, p, s))
    stage2.sort(key=lambda x: x[0])
    winner = stage2[0]
    prior = Policy(0.35, 1.25, 1.0, 1.5, 0.5, 0.5, 0.0)
    baseline_vals = evaluate(prior, validation, SIGMAS, NOISE_SEEDS)
    ladder_vals = []
    for _iid, world, opt in validation:
        ladder_vals.append(expected_cost(world, ladder_chooser, jump_allowed=False) / opt)
    result = {
        "experiment": "adaptive-resolution-scheduler-search-v0.1",
        "status": "development_search_only",
        "candidate_count": len(candidates),
        "train_worlds": len(train),
        "validation_worlds": len(validation),
        "selected_policy": asdict(winner[1]),
        "selected_validation": winner[2],
        "prior_frozen_acquisition_policy_on_resolution": summarize(baseline_vals),
        "fixed_progressive_ladder": summarize(ladder_vals),
        "top_candidates": [{"policy": asdict(p), "summary": s, "objective": round(o, 6)} for o, p, s in stage2[:5]],
        "guardrail": "Development-only search. No sealed resolution seed appears in this file; freeze the selected policy before testing unseen resolution worlds.",
        "caveat": "Synthetic finite-decision resolution mechanics, not end-to-end LLM quality. Fidelity outcomes are nested/coarsened views of a source and acquisition cost is measurable."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
