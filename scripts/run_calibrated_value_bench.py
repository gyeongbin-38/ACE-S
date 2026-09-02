#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "run_information_value_bench.py"
spec = importlib.util.spec_from_file_location("ace_info_value_calibrated", SRC)
bench = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)

SEED = 887_201
INSTANCES_PER_FAMILY = 125
FAMILIES = ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]
SIGMAS = [0.0, 0.10, 0.25, 0.50, 0.75, 1.00, 1.25]
SWITCH_SIGMA = 0.60  # fixed before this independent-seed run from the prior development sweep


def zscore(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)


def noisy(v: float, sigma: float, *key: object) -> float:
    if sigma <= 0 or v <= 0:
        return v
    return v * math.exp(sigma * zscore(SEED, sigma, *key) - 0.5 * sigma * sigma)


def skey(active: tuple[int, ...]) -> str:
    return ",".join(map(str, active))


def value_chooser(iid: int, sigma: float, noisy_cost: bool):
    def choose(inst, active, candidates):
        state = skey(active)
        def score(q):
            ig = noisy(bench.info_gain(inst, active, q), sigma, iid, state, q, "ig")
            cost = noisy(inst.queries[q].cost, sigma, iid, state, q, "cost") if noisy_cost else inst.queries[q].cost
            return (ig / cost, -q)
        return max(candidates, key=score)
    return choose


def cheap_chooser(inst, active, candidates):
    return min(candidates, key=lambda q: (inst.queries[q].cost, q))


def hybrid_chooser(iid: int, sigma: float):
    # Measurable cost is treated as exact. When value calibration becomes too uncertain,
    # use the cheapest informative action rather than trusting a high-variance ratio.
    if sigma > SWITCH_SIGMA:
        return cheap_chooser
    return value_chooser(iid, sigma, noisy_cost=False)


def summarize(vals):
    vals = list(vals)
    ordered = sorted(vals)
    return {
        "mean": round(statistics.fmean(vals), 3),
        "median": round(statistics.median(vals), 3),
        "p90": round(ordered[int(.9 * (len(ordered) - 1))], 3),
    }


def main():
    rng = random.Random(SEED)
    worlds = []
    iid = 0
    for family in FAMILIES:
        for _ in range(INSTANCES_PER_FAMILY):
            inst = bench.make_instance(rng, family)
            opt = bench.optimal_cost(inst)
            load_all = sum(q.cost for q in inst.queries)
            worlds.append((iid, inst, opt, load_all))
            iid += 1

    out = {}
    for sigma in SIGMAS:
        rows = []
        for iid, inst, opt, load_all in worlds:
            exact_cost_value = bench.expected_cost(inst, value_chooser(iid, sigma, noisy_cost=False))
            noisy_both_value = bench.expected_cost(inst, value_chooser(iid, sigma, noisy_cost=True))
            cheap = bench.expected_cost(inst, cheap_chooser)
            hybrid = bench.expected_cost(inst, hybrid_chooser(iid, sigma))
            rows.append({
                "exact_cost_value": exact_cost_value / opt,
                "noisy_both_value": noisy_both_value / opt,
                "cheap": cheap / opt,
                "hybrid": hybrid / opt,
                "hybrid_load_all_reduction": 100 * (1 - hybrid / load_all),
            })
        out[f"sigma_{sigma:.2f}"] = {
            "sigma": sigma,
            "value_with_exact_cost_ratio_to_optimal": summarize(r["exact_cost_value"] for r in rows),
            "value_with_noisy_cost_ratio_to_optimal": summarize(r["noisy_both_value"] for r in rows),
            "cheapest_informative_ratio_to_optimal": summarize(r["cheap"] for r in rows),
            "confidence_gated_hybrid_ratio_to_optimal": summarize(r["hybrid"] for r in rows),
            "hybrid_reduction_vs_load_all_pct": summarize(r["hybrid_load_all_reduction"] for r in rows),
            "hybrid_within_25pct_optimal_rate": round(100 * sum(r["hybrid"] <= 1.25 + 1e-12 for r in rows) / len(rows), 1),
        }

    print(json.dumps({
        "experiment": "calibrated-value-acquisition-independent-seed-v0.1",
        "seed": SEED,
        "instances": len(worlds),
        "families": FAMILIES,
        "switch_sigma": SWITCH_SIGMA,
        "switch_rule": "Use value-per-exact-cost while estimated value noise sigma <= 0.60; otherwise use cheapest currently informative action.",
        "results": out,
        "important_caveat": (
            "Independent synthetic seed. The switch threshold was fixed from the previous noise sweep before this run, but sigma is treated as known calibration uncertainty. "
            "A real controller must estimate that uncertainty from held-out traces. This remains a controller-theory test, not an end-to-end LLM benchmark."
        )
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
