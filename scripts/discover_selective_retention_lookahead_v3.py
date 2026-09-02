#!/usr/bin/env python3
"""Development v3: topology-aware selective depth-3 retention trigger.

V2 used one best quiet-gap pressure score plus an exactness gate. Its sealed OOD
run improved over depth-1, but missed the predeclared gain-capture/deep-use gates.
V3 keeps the trigger cheap and family-agnostic: it detects revival topology after
quiet intervals, semantic ambiguity, and reacquisition pressure. It does not run
depth-3 to decide whether depth-3 is needed.

Development only. Freeze before any new OOD family/seed is introduced.
"""
from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass

import discover_retention_scheduler as ret
from discover_retention_lookahead_depth import FAMILIES, ITEMS_PER_FAMILY, NOISE_SEEDS, SIGMAS, make_item, rollout_cost

SEED = 83_441_907
MAX_DEPTH3_RATE = 0.40


@dataclass(frozen=True)
class Trigger:
    quiet_threshold: float
    revival_threshold: float
    min_quiet_steps: int
    min_revival_segments: int
    pressure_threshold: float
    min_semantic_ambiguity: float


def segment_count(values, threshold):
    count = 0
    active = False
    for value in values:
        now = value >= threshold
        if now and not active:
            count += 1
        active = now
    return count


def topology_features(item: ret.Item, trigger: Trigger):
    p = item.p_need
    best = None
    for cut in range(trigger.min_quiet_steps, len(p) - 1):
        if max(p[cut-trigger.min_quiet_steps:cut]) > trigger.quiet_threshold:
            continue
        future = p[cut:]
        future_need = sum(future)
        if future_need <= 1e-12:
            continue
        exact_mass = sum(pn * pe for pn, pe in zip(future, item.p_exact[cut:]))
        exact_rate = exact_mass / future_need
        # 0 at fully semantic/exact extremes, 1 near a 50/50 exactness mix.
        semantic_ambiguity = 4.0 * exact_rate * (1.0 - exact_rate)
        pressure = item.reacquire_cost * (future_need + 0.75 * exact_mass)
        pressure /= max(item.raw_hold * max(1, len(future)) + item.compact_cost, 1e-12)
        revivals = segment_count(future, trigger.revival_threshold)
        feature = (revivals, pressure, semantic_ambiguity, exact_rate)
        if best is None or (feature[0], feature[1], feature[2]) > (best[0], best[1], best[2]):
            best = feature
    return best or (0, 0.0, 0.0, 1.0)


def fires(item: ret.Item, trigger: Trigger) -> bool:
    revivals, pressure, ambiguity, _exact_rate = topology_features(item, trigger)
    multi_revival = revivals >= trigger.min_revival_segments
    ambiguous_pressure = pressure >= trigger.pressure_threshold and ambiguity >= trigger.min_semantic_ambiguity
    # Multiple revivals are themselves a horizon signal; a single revival needs
    # both economic pressure and semantic ambiguity to justify deeper planning.
    return (multi_revival and pressure >= 0.65 * trigger.pressure_threshold) or ambiguous_pressure


def candidates():
    for quiet in (0.05, 0.07, 0.09):
        for revival in (0.18, 0.25, 0.32):
            for gap in (2, 3):
                for segments in (2, 3):
                    for pressure in (4.0, 6.0, 8.0, 10.0, 12.0):
                        for ambiguity in (0.45, 0.60, 0.75, 0.88):
                            yield Trigger(quiet, revival, gap, segments, pressure, ambiguity)


def summary(vals):
    xs = sorted(vals)
    return {
        "mean": round(statistics.fmean(xs), 5),
        "median": round(statistics.median(xs), 5),
        "p90": round(xs[int(0.90*(len(xs)-1))], 5),
        "p95": round(xs[int(0.95*(len(xs)-1))], 5),
        "within_05pct": round(100*sum(x <= 1.05+1e-12 for x in xs)/len(xs), 2),
        "within_10pct": round(100*sum(x <= 1.10+1e-12 for x in xs)/len(xs), 2),
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
    # Quality first. Among near-equal capture, prefer fewer deep invocations.
    eligible.sort(key=lambda r: (round(r[6], 3), -r[2], -r[4]), reverse=True)
    trigger, selected_ids, rate, vals, mean, gain, capture = eligible[0]

    by_family = {}
    for family in FAMILIES:
        ids = {iid for iid, _item, _opt, fam in items if fam == family}
        fam = [x for x in evals if x[1] == family]
        fam_vals = [d3 if iid in selected_ids else d1 for iid, _f, d1, d3 in fam]
        by_family[family] = {
            "depth3_item_rate_pct": round(100*len(ids & selected_ids)/len(ids), 2),
            "depth1_mean": round(statistics.fmean(x[2] for x in fam), 5),
            "depth3_mean": round(statistics.fmean(x[3] for x in fam), 5),
            "selective_mean": round(statistics.fmean(fam_vals), 5),
        }

    result = {
        "experiment": "selective-retention-lookahead-development-v0.3",
        "status": "development_only",
        "items": len(items),
        "evaluations": len(evals),
        "max_depth3_item_rate_pct": 100*MAX_DEPTH3_RATE,
        "always_depth1": summary([x[2] for x in evals]),
        "always_depth3": summary([x[3] for x in evals]),
        "selected_trigger": asdict(trigger),
        "selected": {
            "depth3_item_rate_pct": round(100*rate, 3),
            "cost_ratio": summary(vals),
            "mean_cost_reduction_vs_depth1_pct": round(100*gain/d1_mean, 3),
            "fraction_of_always_depth3_gain_captured_pct": round(100*capture, 3),
        },
        "by_family": by_family,
        "top_eligible": [
            {"trigger": asdict(t), "depth3_item_rate_pct": round(100*rt,2), "mean_cost_ratio": round(mn,5), "gain_capture_pct": round(100*cp,2)}
            for t,_ids,rt,_vals,mn,_gain,cp in eligible[:12]
        ],
        "guardrail": "Development only. Freeze selected trigger before introducing any new OOD lifecycle families/seed.",
        "claim_boundary": "Synthetic lifecycle economics. Trigger uses generator-level future need/exactness probabilities; deployment needs calibrated estimates. Depth3 invocation rate is a compute proxy.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
