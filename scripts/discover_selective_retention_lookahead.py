#!/usr/bin/env python3
"""Development search for selective depth-3 retention lookahead.

Depth-3 lifecycle planning improves revival-heavy worlds, but always-on deeper
lookahead spends more controller compute. This search derives a deterministic
late-revival score from the lifecycle forecast and uses depth-3 only when the
score crosses a threshold; otherwise it keeps the existing depth-1 rollout.

Development only. True need/exactness probabilities are available in this
synthetic evaluator; a real runtime must estimate them.
"""
from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass

import discover_retention_scheduler as ret
from discover_retention_lookahead_depth import (
    DEV_SEED as SOURCE_DEV_SEED,
    FAMILIES,
    ITEMS_PER_FAMILY,
    NOISE_SEEDS,
    SIGMAS,
    make_item,
    rollout_cost,
)

SEARCH_SEED = SOURCE_DEV_SEED + 901
MAX_DEPTH3_RATE = 0.50


@dataclass(frozen=True)
class Trigger:
    quiet_threshold: float
    min_quiet_steps: int
    score_threshold: float


def late_revival_score(item: ret.Item, quiet_threshold: float, min_quiet_steps: int) -> float:
    """Estimate whether paying deeper planning effort is economically justified.

    Look for a contiguous quiet run followed by substantial future need. The
    score compares expected future reacquisition pressure against the remaining
    RAW-residency + compaction economics. It is deterministic given the forecast.
    """
    p = item.p_need
    horizon = len(p)
    best = 0.0
    for cut in range(min_quiet_steps, horizon - 1):
        quiet = p[cut - min_quiet_steps : cut]
        if max(quiet) > quiet_threshold:
            continue
        future_need = sum(p[cut:])
        future_exact = sum(pn * pe for pn, pe in zip(p[cut:], item.p_exact[cut:]))
        reacquire_pressure = item.reacquire_cost * (future_need + 0.75 * future_exact)
        residency_pressure = item.raw_hold * max(1, horizon - cut) + item.compact_cost
        best = max(best, reacquire_pressure / max(residency_pressure, 1e-12))
    return best


def trigger_depth3(item: ret.Item, trigger: Trigger) -> bool:
    return late_revival_score(item, trigger.quiet_threshold, trigger.min_quiet_steps) >= trigger.score_threshold


def triggers():
    for quiet in (0.06, 0.09, 0.12, 0.16):
        for gap in (2, 3, 4, 5):
            for threshold in (1.0, 1.5, 2.0, 3.0, 4.5, 6.0, 8.0, 12.0):
                yield Trigger(quiet, gap, threshold)


def summarize(vals):
    xs = sorted(vals)
    return {
        "mean": round(statistics.fmean(xs), 5),
        "median": round(statistics.median(xs), 5),
        "p90": round(xs[int(0.90 * (len(xs) - 1))], 5),
        "p95": round(xs[int(0.95 * (len(xs) - 1))], 5),
        "within_05pct": round(100 * sum(x <= 1.05 + 1e-12 for x in xs) / len(xs), 2),
        "within_10pct": round(100 * sum(x <= 1.10 + 1e-12 for x in xs) / len(xs), 2),
    }


def main():
    rng = random.Random(SEARCH_SEED)
    items = []
    iid = 0
    for family in FAMILIES:
        for _ in range(ITEMS_PER_FAMILY):
            item = make_item(rng, family)
            opt = ret.optimal_cost(item)
            items.append((iid, item, opt, family))
            iid += 1

    # Cache depth-1/depth-3 evaluation for every stochastic condition so trigger
    # search itself cannot alter lifecycle decisions.
    eval_rows = []
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid, item, opt, family in items:
                d1 = rollout_cost(item, iid, sigma, nseed, 1) / opt
                d3 = rollout_cost(item, iid, sigma, nseed, 3) / opt
                eval_rows.append((iid, item, family, d1, d3))

    depth1_mean = statistics.fmean(row[3] for row in eval_rows)
    depth3_mean = statistics.fmean(row[4] for row in eval_rows)
    max_possible_gain = depth1_mean - depth3_mean

    rows = []
    for trigger in triggers():
        chosen = []
        invoked_items = {iid for iid, item, _opt, _fam in items if trigger_depth3(item, trigger)}
        rate = len(invoked_items) / len(items)
        for iid, _item, _family, d1, d3 in eval_rows:
            chosen.append(d3 if iid in invoked_items else d1)
        mean = statistics.fmean(chosen)
        gain = depth1_mean - mean
        capture = gain / max_possible_gain if max_possible_gain > 1e-12 else 0.0
        rows.append((trigger, rate, mean, gain, capture, chosen, invoked_items))

    eligible = [r for r in rows if r[1] <= MAX_DEPTH3_RATE + 1e-12 and r[3] > 0]
    # Quality first: maximize captured economic gain. Efficiency second: for
    # nearly equal capture prefer fewer depth-3 invocations.
    eligible.sort(key=lambda r: (round(r[4], 3), -r[1], -r[2]), reverse=True)
    winner = eligible[0]
    trigger, rate, mean, gain, capture, chosen, invoked_items = winner

    by_family = {}
    for family in FAMILIES:
        fam_items = {iid for iid, _item, _opt, fam in items if fam == family}
        fam_rows = [r for r in eval_rows if r[2] == family]
        vals = [r[4] if r[0] in invoked_items else r[3] for r in fam_rows]
        by_family[family] = {
            "depth3_item_rate_pct": round(100 * len(fam_items & invoked_items) / len(fam_items), 2),
            "selective": summarize(vals),
            "depth1_mean": round(statistics.fmean(r[3] for r in fam_rows), 5),
            "depth3_mean": round(statistics.fmean(r[4] for r in fam_rows), 5),
        }

    result = {
        "experiment": "selective-retention-lookahead-development-v0.1",
        "status": "development_only",
        "items": len(items),
        "evaluations": len(eval_rows),
        "max_depth3_item_rate_pct": 100 * MAX_DEPTH3_RATE,
        "always_depth1": summarize([r[3] for r in eval_rows]),
        "always_depth3": summarize([r[4] for r in eval_rows]),
        "selected_trigger": asdict(trigger),
        "selected": {
            "depth3_item_rate_pct": round(100 * rate, 3),
            "cost_ratio": summarize(chosen),
            "mean_cost_reduction_vs_depth1_pct": round(100 * gain / depth1_mean, 3),
            "fraction_of_always_depth3_gain_captured_pct": round(100 * capture, 3),
        },
        "by_family": by_family,
        "top_eligible": [
            {
                "trigger": asdict(t),
                "depth3_item_rate_pct": round(100 * rt, 2),
                "mean_cost_ratio": round(mn, 5),
                "gain_capture_pct": round(100 * cp, 2),
            }
            for t, rt, mn, _g, cp, _v, _ii in eligible[:12]
        ],
        "guardrail": "Development only. Freeze a selected trigger before introducing a new lifecycle seed/families. Prior sealed retention families are already seen and cannot serve as an unseen holdout for this trigger.",
        "claim_boundary": "Synthetic lifecycle economics with true forecast probabilities available to the trigger. Depth-3 invocation rate is a controller-compute proxy, not measured wall-clock or LLM token cost.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
