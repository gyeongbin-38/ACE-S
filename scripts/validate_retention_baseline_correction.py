#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics

import discover_retention_scheduler as ret
import run_second_sealed_scheduler_test as sealed


def corrected_keep_abstract_cost(item: ret.Item) -> float:
    horizon = len(item.p_need)
    total = item.compact_cost + item.abstract_hold * horizon
    for t, (pn, pe) in enumerate(zip(item.p_need, item.p_exact)):
        exact_or_failed = pe + (1.0 - pe) * item.abstract_failure
        # If exact RAW evidence must be reacquired, an always-ABSTRACT policy must
        # compact it again before the next future step. The previous baseline omitted
        # this transition and could therefore appear cheaper than the exact oracle.
        transition = item.reacquire_cost
        if t + 1 < horizon:
            transition += item.compact_cost
        total += pn * exact_or_failed * transition
    return total


def summarize(vals):
    vals = sorted(vals)
    return {
        "mean": round(statistics.fmean(vals), 5),
        "median": round(statistics.median(vals), 5),
        "p90": round(vals[int(0.9 * (len(vals) - 1))], 5),
        "min": round(min(vals), 5),
    }


def main() -> None:
    worlds = sealed.make_retention_worlds(sealed.SEALED_SEED + 1001, 40)
    abstract_ratios = []
    raw_ratios = []
    drop_ratios = []
    for _iid, item, opt, _family in worlds:
        abstract_ratios.append(corrected_keep_abstract_cost(item) / opt)
        raw_ratios.append(ret.baseline_cost(item, ret.RAW) / opt)
        drop_ratios.append(ret.baseline_cost(item, ret.DROP) / opt)
    if min(abstract_ratios) < 1.0 - 1e-9:
        raise AssertionError("corrected keep-abstract policy cannot beat exact oracle")
    if min(raw_ratios) < 1.0 - 1e-9 or min(drop_ratios) < 1.0 - 1e-9:
        raise AssertionError("static feasible policy cannot beat exact oracle")
    print(json.dumps({
        "experiment": "retention-static-baseline-accounting-correction-v0.1",
        "status": "accounting_correction_only_no_policy_change",
        "keep_abstract_corrected": summarize(abstract_ratios),
        "keep_raw": summarize(raw_ratios),
        "drop": summarize(drop_ratios),
        "invariant": "all feasible static policy costs are >= exact dynamic-programming oracle cost",
        "note": "This correction does not alter the frozen retention policy, sealed worlds, exact oracle, keep-raw baseline, or scheduler result. It only fixes the static always-ABSTRACT comparator's missing re-compaction transition."
    }, indent=2))


if __name__ == "__main__":
    main()
