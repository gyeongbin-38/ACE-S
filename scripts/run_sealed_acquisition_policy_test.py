#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SRC = ROOT / "scripts" / "run_information_value_bench.py"
DISCOVERY_SRC = ROOT / "scripts" / "discover_context_acquisition_policy.py"
FROZEN = ROOT / "benchmarks" / "frozen-context-acquisition-policy-v0.1.json"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bench = load_module("ace_sealed_base", BASE_SRC)
disc = load_module("ace_sealed_discovery", DISCOVERY_SRC)

# These seeds were introduced only after benchmarks/frozen-context-acquisition-policy-v0.1.json
# was committed. Do not alter the frozen policy after observing this script's output.
ID_SEED = 1_948_337
OOD_SEED = 7_231_091
NOISE_SEEDS = [81_331, 81_337, 81_347]
SIGMAS = [0.0, 0.25, 0.5, 1.0]
ID_PER_FAMILY = 50
OOD_PER_FAMILY = 75
ID_FAMILIES = ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]
OOD_FAMILIES = ["dominant_prior", "many_decisions", "weak_queries", "correlated", "deceptive_cheap", "flat_cost"]


def normalize(xs: list[float]) -> tuple[float, ...]:
    total = sum(xs)
    return tuple(x / total for x in xs)


def ensure_decision_diversity(rng: random.Random, n_h: int, n_dec: int) -> tuple[int, ...]:
    vals = [i % n_dec for i in range(n_h)]
    rng.shuffle(vals)
    return tuple(vals)


def identity_query(n_h: int, cost: float):
    return bench.Query(tuple(range(n_h)), cost)


def random_binary_query(rng: random.Random, n_h: int, cost: float):
    while True:
        outcomes = tuple(rng.randrange(2) for _ in range(n_h))
        if len(set(outcomes)) > 1:
            return bench.Query(outcomes, cost)


def make_ood_instance(rng: random.Random, family: str):
    if family == "dominant_prior":
        n_h = rng.randint(6, 8)
        decisions = ensure_decision_diversity(rng, n_h, rng.randint(2, 4))
        dominant = rng.randrange(n_h)
        rest = [rng.random() + 0.05 for _ in range(n_h)]
        rest[dominant] = rng.uniform(8.0, 18.0)
        prior = normalize(rest)
        queries = [random_binary_query(rng, n_h, rng.uniform(0.4, 4.0)) for _ in range(rng.randint(4, 6))]
        queries.append(identity_query(n_h, rng.uniform(3.0, 10.0)))

    elif family == "many_decisions":
        n_h = rng.randint(7, 9)
        n_dec = rng.randint(max(4, n_h - 3), n_h)
        decisions = ensure_decision_diversity(rng, n_h, n_dec)
        prior = normalize([rng.uniform(0.6, 1.4) for _ in range(n_h)])
        queries = [random_binary_query(rng, n_h, rng.uniform(0.5, 5.0)) for _ in range(rng.randint(5, 7))]
        queries.append(identity_query(n_h, rng.uniform(4.0, 11.0)))

    elif family == "weak_queries":
        n_h = rng.randint(6, 8)
        decisions = ensure_decision_diversity(rng, n_h, rng.randint(2, 4))
        prior = normalize([rng.random() + 0.2 for _ in range(n_h)])
        # Mostly weak/partial tests, with one expensive complete discriminator.
        queries = []
        for _ in range(rng.randint(5, 7)):
            pivot = rng.randrange(n_h)
            outcomes = tuple(1 if h == pivot else 0 for h in range(n_h))
            queries.append(bench.Query(outcomes, rng.uniform(0.25, 2.2)))
        queries.append(identity_query(n_h, rng.uniform(5.0, 14.0)))

    elif family == "correlated":
        n_h = rng.randint(6, 8)
        decisions = ensure_decision_diversity(rng, n_h, rng.randint(2, 4))
        prior = normalize([rng.random() + 0.1 for _ in range(n_h)])
        base_a = random_binary_query(rng, n_h, 1.0).outcomes
        base_b = random_binary_query(rng, n_h, 1.0).outcomes
        queries = []
        for i in range(rng.randint(5, 7)):
            base = base_a if i % 2 == 0 else base_b
            vals = list(base)
            if rng.random() < 0.65:
                vals[rng.randrange(n_h)] ^= 1
            queries.append(bench.Query(tuple(vals), rng.uniform(0.5, 4.5)))
        queries.append(identity_query(n_h, rng.uniform(4.0, 10.0)))

    elif family == "deceptive_cheap":
        n_h = rng.randint(6, 8)
        decisions = ensure_decision_diversity(rng, n_h, rng.randint(2, 4))
        prior = normalize([rng.random() + 0.2 for _ in range(n_h)])
        queries = []
        # Several very cheap one-hypothesis probes tempt cheapest-first.
        for h in rng.sample(range(n_h), k=min(4, n_h)):
            outcomes = tuple(1 if x == h else 0 for x in range(n_h))
            queries.append(bench.Query(outcomes, rng.uniform(0.08, 0.45)))
        # Medium-cost partitions can resolve decisions much faster.
        for _ in range(2):
            queries.append(random_binary_query(rng, n_h, rng.uniform(0.8, 2.5)))
        queries.append(identity_query(n_h, rng.uniform(2.5, 6.0)))

    elif family == "flat_cost":
        n_h = rng.randint(6, 8)
        decisions = ensure_decision_diversity(rng, n_h, rng.randint(2, 4))
        prior = normalize([rng.random() + 0.2 for _ in range(n_h)])
        queries = [random_binary_query(rng, n_h, rng.uniform(0.9, 1.1)) for _ in range(rng.randint(5, 7))]
        queries.append(identity_query(n_h, rng.uniform(0.9, 1.1)))

    else:
        raise ValueError(family)

    return bench.Instance(decisions, prior, tuple(queries), f"ood:{family}")


def make_worlds():
    worlds = []
    iid = 0
    rng_id = random.Random(ID_SEED)
    for family in ID_FAMILIES:
        for _ in range(ID_PER_FAMILY):
            inst = bench.make_instance(rng_id, family)
            worlds.append((iid, "id", family, inst, bench.optimal_cost(inst)))
            iid += 1

    rng_ood = random.Random(OOD_SEED)
    for family in OOD_FAMILIES:
        for _ in range(OOD_PER_FAMILY):
            inst = make_ood_instance(rng_ood, family)
            worlds.append((iid, "ood", family, inst, bench.optimal_cost(inst)))
            iid += 1
    return worlds


def baseline_chooser(iid: int, sigma: float, noise_seed: int):
    # Current baseline: noisy expected decision information gain / exact measured cost.
    p = disc.Policy(1.0, 1.0, 0.0, 0.0, 0.0, 0.0)
    return disc.chooser(p, iid, sigma, noise_seed)


def summarize(vals: list[float]):
    ordered = sorted(vals)
    return {
        "mean": round(statistics.fmean(vals), 4),
        "median": round(statistics.median(vals), 4),
        "p90": round(ordered[int(0.9 * (len(ordered) - 1))], 4),
        "within_10pct_optimal_rate": round(100 * sum(v <= 1.10 + 1e-12 for v in vals) / len(vals), 1),
        "within_25pct_optimal_rate": round(100 * sum(v <= 1.25 + 1e-12 for v in vals) / len(vals), 1),
    }


def main():
    frozen_obj = json.loads(FROZEN.read_text(encoding="utf-8"))
    if frozen_obj["status"] != "frozen-before-sealed-test":
        raise SystemExit("frozen policy marker missing")
    frozen = disc.Policy(**frozen_obj["policy"])
    worlds = make_worlds()

    rows = []
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, split, family, inst, opt in worlds:
                frozen_cost = bench.expected_cost(inst, disc.chooser(frozen, iid, sigma, nseed))
                baseline_cost = bench.expected_cost(inst, baseline_chooser(iid, sigma, nseed))
                cheapest_cost = bench.expected_cost(inst, bench.choose_cheapest)
                load_all = sum(q.cost for q in inst.queries)
                rows.append({
                    "sigma": sigma,
                    "noise_seed": nseed,
                    "split": split,
                    "family": family,
                    "frozen": frozen_cost / opt,
                    "baseline": baseline_cost / opt,
                    "cheapest": cheapest_cost / opt,
                    "frozen_vs_load_all_reduction_pct": 100 * (1 - frozen_cost / load_all),
                    "frozen_vs_baseline_reduction_pct": 100 * (1 - frozen_cost / baseline_cost),
                    "frozen_beats_baseline": frozen_cost <= baseline_cost + 1e-12,
                })

    def group(predicate):
        rs = [r for r in rows if predicate(r)]
        return {
            "n_evaluations": len(rs),
            "frozen_ratio_to_optimal": summarize([r["frozen"] for r in rs]),
            "current_value_per_cost_ratio_to_optimal": summarize([r["baseline"] for r in rs]),
            "cheapest_ratio_to_optimal": summarize([r["cheapest"] for r in rs]),
            "frozen_mean_reduction_vs_load_all_pct": round(statistics.fmean(r["frozen_vs_load_all_reduction_pct"] for r in rs), 2),
            "frozen_mean_reduction_vs_current_value_per_cost_pct": round(statistics.fmean(r["frozen_vs_baseline_reduction_pct"] for r in rs), 2),
            "frozen_beats_or_ties_current_rate": round(100 * sum(r["frozen_beats_baseline"] for r in rs) / len(rs), 1),
        }

    out = {
        "experiment": "sealed-context-acquisition-policy-test-v0.1",
        "freeze_commit_required": "39ea0218315d109f67562fd5b25ac689ef016e7b",
        "policy": frozen_obj["policy"],
        "worlds": len(worlds),
        "id_worlds": sum(split == "id" for _iid, split, _f, _i, _o in worlds),
        "ood_worlds": sum(split == "ood" for _iid, split, _f, _i, _o in worlds),
        "sigmas": SIGMAS,
        "noise_seeds": NOISE_SEEDS,
        "overall": group(lambda r: True),
        "id": group(lambda r: r["split"] == "id"),
        "ood": group(lambda r: r["split"] == "ood"),
        "by_sigma": {f"sigma_{s:.2f}": group(lambda r, s=s: r["sigma"] == s) for s in SIGMAS},
        "by_ood_family": {f: group(lambda r, f=f: r["split"] == "ood" and r["family"] == f) for f in OOD_FAMILIES},
        "claim_boundary": (
            "The policy was frozen before these seeds/generators were introduced. This is a sealed synthetic controller test, not natural-language signal extraction or end-to-end LLM answer quality. "
            "All compared acquisition strategies continue until decision certainty, so cost is compared at equal synthetic decision correctness."
        )
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
