#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import math
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "scripts" / "run_information_value_bench.py"
spec = importlib.util.spec_from_file_location("ace_info_value_bench", SRC)
bench = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = bench
spec.loader.exec_module(bench)

SEED = 491_773
INSTANCES_PER_FAMILY = 120
NOISE_SIGMAS = [0.0, 0.10, 0.25, 0.50, 1.00]
FAMILIES = ["balanced", "skewed_cost", "high_ig_expensive", "cheap_local"]


def deterministic_normal(*parts: object) -> float:
    raw = "|".join(map(str, parts)).encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    u1 = (int.from_bytes(digest[:8], "big") + 1) / (2**64 + 1)
    u2 = (int.from_bytes(digest[8:16], "big") + 1) / (2**64 + 1)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def noisy_positive(true_value: float, sigma: float, *key: object) -> float:
    if sigma == 0.0 or true_value <= 0.0:
        return true_value
    z = deterministic_normal(SEED, sigma, *key)
    # Mean-preserving log-normal multiplicative error.
    return true_value * math.exp(sigma * z - 0.5 * sigma * sigma)


def state_key(active: tuple[int, ...]) -> str:
    return ",".join(map(str, active))


def noisy_value_chooser(instance_id: int, sigma: float):
    def choose(inst, active: tuple[int, ...], candidates: list[int]) -> int:
        skey = state_key(active)
        return max(
            candidates,
            key=lambda q: (
                noisy_positive(bench.info_gain(inst, active, q), sigma, instance_id, skey, q, "ig")
                / noisy_positive(inst.queries[q].cost, sigma, instance_id, skey, q, "cost"),
                -q,
            ),
        )
    return choose


def noisy_ig_chooser(instance_id: int, sigma: float):
    def choose(inst, active: tuple[int, ...], candidates: list[int]) -> int:
        skey = state_key(active)
        return max(
            candidates,
            key=lambda q: (
                noisy_positive(bench.info_gain(inst, active, q), sigma, instance_id, skey, q, "ig"),
                -q,
            ),
        )
    return choose


def noisy_cheapest_chooser(instance_id: int, sigma: float):
    def choose(inst, active: tuple[int, ...], candidates: list[int]) -> int:
        skey = state_key(active)
        return min(
            candidates,
            key=lambda q: (
                noisy_positive(inst.queries[q].cost, sigma, instance_id, skey, q, "cost"),
                q,
            ),
        )
    return choose


def summarize(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "mean": round(statistics.fmean(values), 3),
        "median": round(statistics.median(values), 3),
        "p90": round(ordered[int(0.9 * (len(ordered) - 1))], 3),
    }


def main() -> None:
    rng = random.Random(SEED)
    instances: list[tuple[int, object, float, float]] = []
    iid = 0
    for family in FAMILIES:
        for _ in range(INSTANCES_PER_FAMILY):
            inst = bench.make_instance(rng, family)
            opt = bench.optimal_cost(inst)
            load_all = sum(q.cost for q in inst.queries)
            instances.append((iid, inst, opt, load_all))
            iid += 1

    results = {}
    for sigma in NOISE_SIGMAS:
        rows = []
        for iid, inst, opt, load_all in instances:
            value = bench.expected_cost(inst, noisy_value_chooser(iid, sigma))
            ig = bench.expected_cost(inst, noisy_ig_chooser(iid, sigma))
            cheap = bench.expected_cost(inst, noisy_cheapest_chooser(iid, sigma))
            rows.append(
                {
                    "value_ratio": value / opt,
                    "ig_ratio": ig / opt,
                    "cheap_ratio": cheap / opt,
                    "value_vs_all_reduction": 100.0 * (1.0 - value / load_all),
                    "value_beats_ig": value <= ig + 1e-12,
                    "value_beats_cheap": value <= cheap + 1e-12,
                    "within_10": value <= 1.10 * opt + 1e-12,
                    "within_25": value <= 1.25 * opt + 1e-12,
                }
            )
        key = f"sigma_{sigma:.2f}"
        results[key] = {
            "multiplicative_noise_sigma": sigma,
            "value_ratio_to_optimal": summarize([r["value_ratio"] for r in rows]),
            "info_gain_ratio_to_optimal": summarize([r["ig_ratio"] for r in rows]),
            "cheapest_ratio_to_optimal": summarize([r["cheap_ratio"] for r in rows]),
            "value_reduction_vs_load_all_pct": summarize([r["value_vs_all_reduction"] for r in rows]),
            "value_within_10pct_optimal_rate": round(100 * sum(r["within_10"] for r in rows) / len(rows), 1),
            "value_within_25pct_optimal_rate": round(100 * sum(r["within_25"] for r in rows) / len(rows), 1),
            "value_beats_or_ties_noisy_info_gain_rate": round(100 * sum(r["value_beats_ig"] for r in rows) / len(rows), 1),
            "value_beats_or_ties_noisy_cheapest_rate": round(100 * sum(r["value_beats_cheap"] for r in rows) / len(rows), 1),
        }

    import json
    print(
        json.dumps(
            {
                "experiment": "value-per-context-cost-noise-robustness-v0.1",
                "seed": SEED,
                "instances": len(instances),
                "families": FAMILIES,
                "noise_model": (
                    "Independent mean-preserving log-normal multiplicative noise is applied to estimated decision information gain and estimated acquisition cost at each state/query choice. "
                    "Evaluation always uses true acquisition cost and exact dynamic-programming optimal cost."
                ),
                "results": results,
                "important_caveat": (
                    "Synthetic robustness test. Noise is stochastic calibration error over a finite deterministic evidence world, not an empirical error distribution from an LLM classifier. "
                    "The purpose is to test whether the value-per-cost policy collapses when its estimates are imperfect before attempting real-agent calibration."
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
