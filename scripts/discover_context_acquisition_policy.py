#!/usr/bin/env python3
from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "run_information_value_bench.py"
spec = importlib.util.spec_from_file_location("ace_info_value_discovery", SRC)
bench = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)

# These seeds are development-only. No sealed-test seed exists in this file.
TRAIN_SEED = 311_771
VALIDATION_SEED = 662_903
SEARCH_NOISE_SEED = 190_081
VALIDATION_NOISE_SEEDS = [502_101, 502_103]
FAMILIES = ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]
SEARCH_WORLDS_PER_FAMILY = 8
VALIDATION_WORLDS_PER_FAMILY = 16
SEARCH_SIGMAS = [0.0, 0.5, 1.0]
VALIDATION_SIGMAS = [0.0, 0.25, 0.5, 1.0]
CANDIDATE_COUNT = 384


@dataclass(frozen=True)
class Policy:
    ig_exp: float
    cost_exp: float
    gini_weight: float
    solve_weight: float
    worst_weight: float
    count_weight: float


def decision_mass(inst, active: tuple[int, ...]) -> dict[int, float]:
    total = sum(inst.prior[h] for h in active)
    out: dict[int, float] = {}
    for h in active:
        d = inst.decisions[h]
        out[d] = out.get(d, 0.0) + inst.prior[h] / total
    return out


def gini(inst, active: tuple[int, ...]) -> float:
    return 1.0 - sum(p * p for p in decision_mass(inst, active).values())


def gini_gain(inst, active: tuple[int, ...], qid: int) -> float:
    before = gini(inst, active)
    after = sum(prob * gini(inst, state) for prob, state in bench.partitions(inst, active, qid))
    return max(0.0, before - after)


def solve_probability(inst, active: tuple[int, ...], qid: int) -> float:
    return sum(prob for prob, state in bench.partitions(inst, active, qid) if bench.solved(inst, state))


def worst_entropy_gain(inst, active: tuple[int, ...], qid: int) -> float:
    before = bench.decision_entropy(inst, active)
    worst_after = max(bench.decision_entropy(inst, state) for _prob, state in bench.partitions(inst, active, qid))
    return max(0.0, before - worst_after)


def decision_count(inst, active: tuple[int, ...]) -> int:
    return len({inst.decisions[h] for h in active})


def count_gain(inst, active: tuple[int, ...], qid: int) -> float:
    before = decision_count(inst, active)
    if before <= 1:
        return 0.0
    after = sum(prob * decision_count(inst, state) for prob, state in bench.partitions(inst, active, qid))
    return max(0.0, before - after) / (before - 1)


def zscore(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def noisy_positive(value: float, sigma: float, noise_seed: int, *key: object) -> float:
    if sigma <= 0.0 or value <= 0.0:
        return value
    z = zscore(noise_seed, sigma, *key)
    return value * math.exp(sigma * z - 0.5 * sigma * sigma)


def chooser(policy: Policy, iid: int, sigma: float, noise_seed: int):
    def choose(inst, active: tuple[int, ...], candidates: list[int]) -> int:
        skey = ",".join(map(str, active))
        def score(q: int) -> tuple[float, float, int]:
            # Value-side estimates may be noisy. Acquisition cost is deliberately exact/measured.
            ig = noisy_positive(bench.info_gain(inst, active, q), sigma, noise_seed, iid, skey, q, "ig")
            gg = noisy_positive(gini_gain(inst, active, q), sigma, noise_seed, iid, skey, q, "gini")
            sp = min(1.0, noisy_positive(solve_probability(inst, active, q), sigma, noise_seed, iid, skey, q, "solve"))
            wg = noisy_positive(worst_entropy_gain(inst, active, q), sigma, noise_seed, iid, skey, q, "worst")
            cg = noisy_positive(count_gain(inst, active, q), sigma, noise_seed, iid, skey, q, "count")
            value = (
                ig ** policy.ig_exp
                + policy.gini_weight * gg
                + policy.solve_weight * sp
                + policy.worst_weight * wg
                + policy.count_weight * cg
            )
            cost = inst.queries[q].cost
            return (value / (cost ** policy.cost_exp), -cost, -q)
        return max(candidates, key=score)
    return choose


def make_worlds(seed: int, per_family: int):
    rng = random.Random(seed)
    worlds = []
    iid = 0
    for family in FAMILIES:
        for _ in range(per_family):
            inst = bench.make_instance(rng, family)
            worlds.append((iid, inst, bench.optimal_cost(inst)))
            iid += 1
    return worlds


def summarize(vals: list[float]) -> dict:
    ordered = sorted(vals)
    return {
        "mean": round(statistics.fmean(vals), 5),
        "median": round(statistics.median(vals), 5),
        "p90": round(ordered[int(0.9 * (len(ordered) - 1))], 5),
        "within_10pct": round(100 * sum(v <= 1.10 + 1e-12 for v in vals) / len(vals), 2),
    }


def candidate_space() -> list[Policy]:
    # Broad but bounded symbolic family. Deterministic sampling prevents manual cherry-picking.
    rng = random.Random(92_441)
    axes = {
        "ig_exp": [0.25, 0.35, 0.5, 0.65, 0.8, 1.0],
        "cost_exp": [0.75, 1.0, 1.25, 1.5, 1.75],
        "gini_weight": [0.0, 0.25, 0.5, 1.0],
        "solve_weight": [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0],
        "worst_weight": [0.0, 0.25, 0.5, 1.0],
        "count_weight": [0.0, 0.25, 0.5, 1.0],
    }
    seen: set[Policy] = set()
    # Always include the current value/cost baseline exactly.
    seen.add(Policy(1.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    while len(seen) < CANDIDATE_COUNT:
        seen.add(Policy(
            rng.choice(axes["ig_exp"]),
            rng.choice(axes["cost_exp"]),
            rng.choice(axes["gini_weight"]),
            rng.choice(axes["solve_weight"]),
            rng.choice(axes["worst_weight"]),
            rng.choice(axes["count_weight"]),
        ))
    return sorted(seen, key=lambda p: tuple(asdict(p).values()))


def evaluate(policy: Policy, worlds, sigmas, noise_seeds) -> tuple[float, float, list[float]]:
    ratios: list[float] = []
    for sigma in sigmas:
        for nseed in noise_seeds:
            for iid, inst, opt in worlds:
                cost = bench.expected_cost(inst, chooser(policy, iid, sigma, nseed))
                ratios.append(cost / opt)
    ordered = sorted(ratios)
    mean = statistics.fmean(ratios)
    p90 = ordered[int(0.9 * (len(ordered) - 1))]
    objective = mean + 0.30 * max(0.0, p90 - 1.0)
    return objective, mean, ratios


def main() -> None:
    train = make_worlds(TRAIN_SEED, SEARCH_WORLDS_PER_FAMILY)
    validation = make_worlds(VALIDATION_SEED, VALIDATION_WORLDS_PER_FAMILY)
    candidates = candidate_space()

    stage1 = []
    for p in candidates:
        objective, mean, ratios = evaluate(p, train, SEARCH_SIGMAS, [SEARCH_NOISE_SEED])
        stage1.append((objective, mean, p, summarize(ratios)))
    stage1.sort(key=lambda row: (row[0], row[1], tuple(asdict(row[2]).values())))

    # Only validation chooses among the top development candidates.
    finalists = stage1[:16]
    stage2 = []
    for _obj, _mean, p, _summary in finalists:
        objective, mean, ratios = evaluate(p, validation, VALIDATION_SIGMAS, VALIDATION_NOISE_SEEDS)
        stage2.append((objective, mean, p, summarize(ratios)))
    stage2.sort(key=lambda row: (row[0], row[1], tuple(asdict(row[2]).values())))

    winner = stage2[0]
    baseline = Policy(1.0, 1.0, 0.0, 0.0, 0.0, 0.0)
    _bobj, _bmean, bratios = evaluate(baseline, validation, VALIDATION_SIGMAS, VALIDATION_NOISE_SEEDS)

    result = {
        "experiment": "context-acquisition-symbolic-policy-search-v0.1",
        "status": "development_search_only",
        "candidate_count": len(candidates),
        "train_worlds": len(train),
        "validation_worlds": len(validation),
        "search_sigmas": SEARCH_SIGMAS,
        "validation_sigmas": VALIDATION_SIGMAS,
        "selected_policy": asdict(winner[2]),
        "selected_validation": winner[3],
        "current_value_per_cost_validation": summarize(bratios),
        "top_validation_candidates": [
            {"policy": asdict(p), "objective": round(obj, 6), "summary": summary}
            for obj, _mean, p, summary in stage2[:5]
        ],
        "guardrail": (
            "This script contains no sealed-test seed. Freeze selected_policy in a separate commit before creating or running any sealed test. "
            "Exact acquisition cost is treated as measurable; uncertainty is injected only into value-side estimates."
        ),
        "caveat": "Synthetic finite-decision policy discovery, not LLM answer-quality evidence."
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
