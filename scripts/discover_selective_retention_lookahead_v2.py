#!/usr/bin/env python3
"""Development v2 selective depth-3 retention trigger.

V1 recovered 83.7% of always-depth3 economic gain while invoking depth3 for
48.9% of items, but over-triggered badly on an obvious late exactness burst where
depth1 was already optimal. V2 adds an ambiguity gate: deep lookahead is reserved
for revival cases whose future need is not overwhelmingly exact/raw-obvious.

Development only.
"""
from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass

import discover_retention_scheduler as ret
from discover_retention_lookahead_depth import FAMILIES, ITEMS_PER_FAMILY, NOISE_SEEDS, SIGMAS, make_item, rollout_cost

SEED = 61_903_771
MAX_DEPTH3_RATE = 0.40


@dataclass(frozen=True)
class Trigger:
    quiet_threshold: float
    min_quiet_steps: int
    score_threshold: float
    max_future_exact_rate: float


def best_revival_features(item: ret.Item, quiet_threshold: float, min_quiet_steps: int):
    best_score = 0.0
    best_exact_rate = 1.0
    p = item.p_need
    for cut in range(min_quiet_steps, len(p) - 1):
        if max(p[cut - min_quiet_steps : cut]) > quiet_threshold:
            continue
        future_need = sum(p[cut:])
        if future_need <= 1e-12:
            continue
        future_exact_mass = sum(pn * pe for pn, pe in zip(p[cut:], item.p_exact[cut:]))
        exact_rate = future_exact_mass / future_need
        reacquire_pressure = item.reacquire_cost * (future_need + 0.75 * future_exact_mass)
        residency_pressure = item.raw_hold * max(1, len(p) - cut) + item.compact_cost
        score = reacquire_pressure / max(residency_pressure, 1e-12)
        if score > best_score:
            best_score = score
            best_exact_rate = exact_rate
    return best_score, best_exact_rate


def fires(item: ret.Item, trigger: Trigger) -> bool:
    score, exact_rate = best_revival_features(item, trigger.quiet_threshold, trigger.min_quiet_steps)
    return score >= trigger.score_threshold and exact_rate <= trigger.max_future_exact_rate


def candidates():
    for quiet in (0.05, 0.06, 0.08, 0.10):
        for gap in (2, 3, 4):
            for score in (3.0, 4.5, 6.0, 8.0, 10.0, 12.0):
                for exact in (0.55, 0.65, 0.75, 0.85, 0.95):
                    yield Trigger(quiet, gap, score, exact)


def summary(vals):
    xs = sorted(vals)
    return {
        "mean": round(statistics.fmean(xs), 5),
        "median": round(statistics.median(xs), 5),
        "p90": round(xs[int(0.90 * (len(xs)-1))], 5),
        "p95": round(xs[int(0.95 * (len(xs)-1))], 5),
        "within_05pct": round(100 * sum(x <= 1.05 + 1e-12 for x in xs) / len(xs), 2),
        "within_10pct": round(100 * sum(x <= 1.10 + 1e-12 for x in xs) / len(xs), 2),
    }


def main():
    rng = random.Random(SEED)
    items = []
    iid = 0
    for family in FAMILIES:
        for _ in range(ITEMS_PER_FAMILY):
            item = make_item(rng, family)
            items.append((iid, item, ret.optimal_cost(item), family))
            iid += 1

    evals = []
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                d1 = rollout_cost(item, iid, sigma, nseed, 1) / opt
                d3 = rollout_cost(item, iid, sigma, nseed, 3) / opt
                evals.append((iid, family, d1, d3))

    d1_mean = statistics.fmean(x[2] for x in evals)
    d3_mean = statistics.fmean(x[3] for x in evals)
    full_gain = d1_mean - d3_mean
    rows = []
    for trigger in candidates():
        selected_ids = {iid for iid, item, _opt, _family in items if fires(item, trigger)}
        rate = len(selected_ids) / len(items)
        vals = [d3 if iid in selected_ids else d1 for iid, _fam, d1, d3 in evals]
        mean = statistics.fmean(vals)
        gain = d1_mean - mean
        capture = gain / full_gain if full_gain > 1e-12 else 0.0
        rows.append((trigger, selected_ids, rate, vals, mean, gain, capture))

    eligible = [r for r in rows if r[2] <= MAX_DEPTH3_RATE + 1e-12 and r[5] > 0]
    # Quality-first: maximize captured gain; then use fewer deep invocations.
    eligible.sort(key=lambda r: (round(r[6], 4), -r[2], -r[4]), reverse=True)
    trigger, selected_ids, rate, vals, mean, gain, capture = eligible[0]

    by_family = {}
    for family in FAMILIES:
        family_ids = {iid for iid, _item, _opt, fam in items if fam == family}
        fam_evals = [x for x in evals if x[1] == family]
        fam_vals = [d3 if iid in selected_ids else d1 for iid, _fam, d1, d3 in fam_evals]
        by_family[family] = {
            "depth3_item_rate_pct": round(100 * len(family_ids & selected_ids) / len(family_ids), 2),
            "selective_mean": round(statistics.fmean(fam_vals), 5),
            "depth1_mean": round(statistics.fmean(x[2] for x in fam_evals), 5),
            "depth3_mean": round(statistics.fmean(x[3] for x in fam_evals), 5),
        }

    result = {
        "experiment": "selective-retention-lookahead-development-v0.2",
        "status": "development_only",
        "items": len(items),
        "evaluations": len(evals),
        "max_depth3_item_rate_pct": 100 * MAX_DEPTH3_RATE,
        "always_depth1": summary([x[2] for x in evals]),
        "always_depth3": summary([x[3] for x in evals]),
        "selected_trigger": asdict(trigger),
        "selected": {
            "depth3_item_rate_pct": round(100 * rate, 3),
            "cost_ratio": summary(vals),
            "mean_cost_reduction_vs_depth1_pct": round(100 * gain / d1_mean, 3),
            "fraction_of_always_depth3_gain_captured_pct": round(100 * capture, 3),
        },
        "by_family": by_family,
        "top_eligible": [
            {"trigger": asdict(t), "depth3_item_rate_pct": round(100 * rt, 2), "mean_cost_ratio": round(mn, 5), "gain_capture_pct": round(100 * cp, 2)}
            for t, _ids, rt, _vals, mn, _gain, cp in eligible[:12]
        ],
        "guardrail": "Development only. Freeze before new lifecycle families/seed. Prior retention sealed suites are now seen and cannot be reused as an unseen holdout.",
        "claim_boundary": "Synthetic lifecycle economics. Future exactness and need are true generator probabilities here; real deployment requires calibrated estimates. Invocation rate is a compute proxy, not wall-clock measurement.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
