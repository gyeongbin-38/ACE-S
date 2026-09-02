#!/usr/bin/env python3
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import dataclass

SEED = 380013
INSTANCES_PER_FAMILY = 250


@dataclass(frozen=True)
class Query:
    outcomes: tuple[int, ...]
    cost: float


@dataclass(frozen=True)
class Instance:
    decisions: tuple[int, ...]
    prior: tuple[float, ...]
    queries: tuple[Query, ...]
    family: str


def entropy(probs: list[float]) -> float:
    return -sum(p * math.log2(p) for p in probs if p > 0)


def normalize(weights: list[float]) -> list[float]:
    s = sum(weights)
    return [w / s for w in weights]


def decision_entropy(inst: Instance, active: tuple[int, ...]) -> float:
    mass: dict[int, float] = {}
    total = sum(inst.prior[h] for h in active)
    for h in active:
        mass[inst.decisions[h]] = mass.get(inst.decisions[h], 0.0) + inst.prior[h] / total
    return entropy(list(mass.values()))


def solved(inst: Instance, active: tuple[int, ...]) -> bool:
    return len({inst.decisions[h] for h in active}) <= 1


def partitions(inst: Instance, active: tuple[int, ...], qid: int) -> list[tuple[float, tuple[int, ...]]]:
    buckets: dict[int, list[int]] = {}
    for h in active:
        buckets.setdefault(inst.queries[qid].outcomes[h], []).append(h)
    total = sum(inst.prior[h] for h in active)
    out = []
    for hs in buckets.values():
        state = tuple(hs)
        prob = sum(inst.prior[h] for h in state) / total
        out.append((prob, state))
    return out


def info_gain(inst: Instance, active: tuple[int, ...], qid: int) -> float:
    before = decision_entropy(inst, active)
    after = sum(prob * decision_entropy(inst, state) for prob, state in partitions(inst, active, qid))
    return max(0.0, before - after)


def useful(inst: Instance, active: tuple[int, ...], qid: int) -> bool:
    return info_gain(inst, active, qid) > 1e-12


def expected_cost(inst: Instance, chooser) -> float:
    all_h = tuple(range(len(inst.decisions)))
    all_q = tuple(range(len(inst.queries)))

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], remaining: tuple[int, ...]) -> float:
        if solved(inst, active):
            return 0.0
        candidates = [q for q in remaining if useful(inst, active, q)]
        if not candidates:
            return math.inf
        qid = chooser(inst, active, candidates)
        next_remaining = tuple(q for q in remaining if q != qid)
        return inst.queries[qid].cost + sum(prob * rec(state, next_remaining) for prob, state in partitions(inst, active, qid))

    return rec(all_h, all_q)


def optimal_cost(inst: Instance) -> float:
    all_h = tuple(range(len(inst.decisions)))
    all_q = tuple(range(len(inst.queries)))

    @functools.lru_cache(maxsize=None)
    def rec(active: tuple[int, ...], remaining: tuple[int, ...]) -> float:
        if solved(inst, active):
            return 0.0
        best = math.inf
        for qid in remaining:
            if not useful(inst, active, qid):
                continue
            next_remaining = tuple(q for q in remaining if q != qid)
            tail = sum(prob * rec(state, next_remaining) for prob, state in partitions(inst, active, qid))
            best = min(best, inst.queries[qid].cost + tail)
        return best

    return rec(all_h, all_q)


def choose_ig(inst: Instance, active: tuple[int, ...], candidates: list[int]) -> int:
    return max(candidates, key=lambda q: (info_gain(inst, active, q), -inst.queries[q].cost, -q))


def choose_cheapest(inst: Instance, active: tuple[int, ...], candidates: list[int]) -> int:
    return min(candidates, key=lambda q: (inst.queries[q].cost, -info_gain(inst, active, q), q))


def choose_value(inst: Instance, active: tuple[int, ...], candidates: list[int]) -> int:
    return max(
        candidates,
        key=lambda q: (
            info_gain(inst, active, q) / inst.queries[q].cost,
            info_gain(inst, active, q),
            -inst.queries[q].cost,
            -q,
        ),
    )


def separates_decisions(decisions: tuple[int, ...], queries: list[Query]) -> bool:
    n = len(decisions)
    for i in range(n):
        for j in range(i + 1, n):
            if decisions[i] == decisions[j]:
                continue
            if not any(q.outcomes[i] != q.outcomes[j] for q in queries):
                return False
    return True


def make_instance(rng: random.Random, family: str) -> Instance:
    for _ in range(1000):
        n = rng.randint(6, 9)
        k = rng.randint(2, min(4, n))
        decisions = tuple(rng.randrange(k) for _ in range(n))
        if len(set(decisions)) < 2:
            continue
        prior = tuple(normalize([0.15 + rng.random() ** 2 for _ in range(n)]))
        qn = rng.randint(5, 8)
        raw_queries: list[Query] = []
        for _qid in range(qn):
            arity = 2 if rng.random() < 0.75 else 3
            outcomes = tuple(rng.randrange(arity) for _ in range(n))
            if len(set(outcomes)) < 2:
                continue
            if family == "balanced":
                cost = rng.uniform(2.0, 12.0)
            elif family == "skewed_cost":
                cost = math.exp(rng.uniform(math.log(1.0), math.log(80.0)))
            elif family == "cheap_local":
                cost = rng.uniform(0.7, 5.0)
            else:
                cost = rng.uniform(1.0, 12.0)
            raw_queries.append(Query(outcomes, cost))
        if len(raw_queries) < 4 or not separates_decisions(decisions, raw_queries):
            continue
        inst = Instance(decisions, prior, tuple(raw_queries), family)
        if family == "high_ig_expensive":
            active = tuple(range(n))
            best_ig = max(range(len(inst.queries)), key=lambda q: info_gain(inst, active, q))
            qs = list(inst.queries)
            qs[best_ig] = Query(qs[best_ig].outcomes, rng.uniform(35.0, 90.0))
            inst = Instance(decisions, prior, tuple(qs), family)
        if family == "cheap_local":
            # Add one expensive broad query so a relevance-only strategy has a tempting shortcut.
            broad = tuple(decisions)
            inst = Instance(decisions, prior, inst.queries + (Query(broad, rng.uniform(20.0, 45.0)),), family)
        opt = optimal_cost(inst)
        if math.isfinite(opt) and opt > 0:
            return inst
    raise RuntimeError(f"failed to generate solvable instance for {family}")


def pct_reduction(value: float, baseline: float) -> float:
    return 100.0 * (1.0 - value / baseline)


def summarize(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows]
    return {
        "mean": round(statistics.fmean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "p90": round(sorted(vals)[int(0.9 * (len(vals) - 1))], 3),
    }


def main() -> None:
    rng = random.Random(SEED)
    families = ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]
    rows: list[dict] = []
    by_family: dict[str, list[dict]] = {f: [] for f in families}

    for family in families:
        for _ in range(INSTANCES_PER_FAMILY):
            inst = make_instance(rng, family)
            opt = optimal_cost(inst)
            value = expected_cost(inst, choose_value)
            ig = expected_cost(inst, choose_ig)
            cheap = expected_cost(inst, choose_cheapest)
            load_all = sum(q.cost for q in inst.queries)
            row = {
                "family": family,
                "optimal": opt,
                "value_per_cost": value,
                "info_gain_only": ig,
                "cheapest_first": cheap,
                "load_all": load_all,
                "value_ratio_to_optimal": value / opt,
                "ig_ratio_to_optimal": ig / opt,
                "cheap_ratio_to_optimal": cheap / opt,
                "value_reduction_vs_load_all_pct": pct_reduction(value, load_all),
                "value_reduction_vs_info_gain_pct": pct_reduction(value, ig),
            }
            rows.append(row)
            by_family[family].append(row)

    result = {
        "experiment": "information-value-per-context-cost-v0.1",
        "seed": SEED,
        "instances": len(rows),
        "families": families,
        "goal": "Reach decision certainty in finite-hypothesis worlds with minimum expected context-action cost.",
        "strategies": {
            "load_all": "Acquire every available evidence action.",
            "info_gain_only": "Greedy expected decision information gain, ignoring cost.",
            "cheapest_first": "Cheapest currently informative action.",
            "value_per_cost": "Greedy expected decision information gain divided by explicit acquisition cost.",
            "optimal": "Exact dynamic-programming minimum expected cost; evaluation oracle only."
        },
        "overall": {
            "value_ratio_to_optimal": summarize(rows, "value_ratio_to_optimal"),
            "ig_ratio_to_optimal": summarize(rows, "ig_ratio_to_optimal"),
            "cheap_ratio_to_optimal": summarize(rows, "cheap_ratio_to_optimal"),
            "value_reduction_vs_load_all_pct": summarize(rows, "value_reduction_vs_load_all_pct"),
            "value_reduction_vs_info_gain_pct": summarize(rows, "value_reduction_vs_info_gain_pct"),
            "near_optimal_within_10pct_rate": round(100 * sum(r["value_ratio_to_optimal"] <= 1.10 + 1e-12 for r in rows) / len(rows), 1),
            "beats_or_ties_info_gain_rate": round(100 * sum(r["value_per_cost"] <= r["info_gain_only"] + 1e-12 for r in rows) / len(rows), 1),
            "beats_or_ties_cheapest_rate": round(100 * sum(r["value_per_cost"] <= r["cheapest_first"] + 1e-12 for r in rows) / len(rows), 1)
        },
        "by_family": {},
        "important_caveat": (
            "Synthetic controller-theory stress test, not an LLM task benchmark. Queries reveal deterministic outcomes in small finite worlds and cost is explicit. "
            "It tests the acquisition policy principle independently of prompt wording; real systems still need calibrated estimates of decision information/value and effective cost."
        )
    }
    for family, fam_rows in by_family.items():
        result["by_family"][family] = {
            "n": len(fam_rows),
            "value_ratio_to_optimal": summarize(fam_rows, "value_ratio_to_optimal"),
            "value_reduction_vs_load_all_pct": summarize(fam_rows, "value_reduction_vs_load_all_pct"),
            "value_reduction_vs_info_gain_pct": summarize(fam_rows, "value_reduction_vs_info_gain_pct"),
            "near_optimal_within_10pct_rate": round(100 * sum(r["value_ratio_to_optimal"] <= 1.10 + 1e-12 for r in fam_rows) / len(fam_rows), 1)
        }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
