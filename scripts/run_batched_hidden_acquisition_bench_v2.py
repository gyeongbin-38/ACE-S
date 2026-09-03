#!/usr/bin/env python3
"""Development v2: adaptive batching for hidden structured acquisition.

Compares exact policies where pair bundles are available only when measured shared
call overhead clears a threshold. This tests whether batching can recover the
call-count penalty of controller/worker exposure separation without forcing
bundles in low-overhead cases.

Synthetic mechanics only. Development search; freeze before sealed OOD use.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

from run_batched_hidden_acquisition_bench import World, acquisition_cost, bundle_cost, gen_world, partitions, narrow, action_outcome, summary

SEED = 9_210_331 + 41_009
WORLDS = 300
THRESHOLDS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]


def exact_policy(world: World, threshold: float | None):
    n = len(world.actions)
    initial = tuple(range(world.n))

    @functools.lru_cache(None)
    def dp(controller, worker, used_mask, hidden_mask):
        if world.solved(controller) and world.solved(worker):
            return 0.0, 0.0, 0.0, 0.0
        best = (math.inf, math.inf, math.inf, math.inf)

        for idx in range(n):
            if not (hidden_mask & (1 << idx)):
                continue
            action = world.actions[idx]
            outcomes = {action_outcome(action, i) for i in controller}
            if len(outcomes) != 1:
                continue
            obs = next(iter(outcomes))
            w2 = narrow(worker, action, obs)
            if w2 == worker:
                continue
            child = dp(controller, w2, used_mask, hidden_mask & ~(1 << idx))
            exp = action["exposure_cost"]
            cand = (exp + child[0], child[1], exp + child[2], child[3])
            if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                best = cand

        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, controller, (idx,))
            known = len(parts) == 1
            if known and action["kind"] != "semantic":
                continue
            if known:
                obs = parts[0][1][0]
                w2 = narrow(worker, action, obs)
                if w2 == worker:
                    continue
                child = dp(controller, w2, used_mask | (1 << idx), hidden_mask)
                acq = acquisition_cost(action); exp = action["exposure_cost"]
                cand = (acq + exp + child[0], acq + child[1], exp + child[2], 1 + child[3])
                if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                    best = cand
                continue
            acq = acquisition_cost(action)
            exp = action["exposure_cost"] if action["kind"] == "semantic" else 0.0
            total, ea, ee, calls = acq + exp, acq, exp, 1.0
            next_used = used_mask | (1 << idx)
            next_hidden = hidden_mask | (1 << idx) if action["kind"] == "structured" else hidden_mask
            feasible = True
            for p, key, c2 in parts:
                w2 = worker
                if action["kind"] == "semantic":
                    w2 = narrow(worker, action, key[0])
                child = dp(c2, w2, next_used, next_hidden)
                if not math.isfinite(child[0]):
                    feasible = False; break
                total += p * child[0]; ea += p * child[1]; ee += p * child[2]; calls += p * child[3]
            if feasible:
                cand = (total, ea, ee, calls)
                if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                    best = cand

        if threshold is not None:
            candidates = [i for i, a in enumerate(world.actions) if not (used_mask & (1 << i)) and a["kind"] == "structured" and a["batchable"]]
            for pos, i in enumerate(candidates):
                ai = world.actions[i]
                for j in candidates[pos + 1:]:
                    aj = world.actions[j]
                    if ai["backend"] != aj["backend"]:
                        continue
                    # Shared-overhead saving from pair acquisition versus two singles.
                    saving = acquisition_cost(ai) + acquisition_cost(aj) - bundle_cost(ai, aj)
                    if saving + 1e-12 < threshold:
                        continue
                    parts = partitions(world, controller, (i, j))
                    if len(parts) <= 1:
                        continue
                    acq = bundle_cost(ai, aj)
                    total, ea, ee, calls = acq, acq, 0.0, 1.0
                    next_used = used_mask | (1 << i) | (1 << j)
                    next_hidden = hidden_mask | (1 << i) | (1 << j)
                    feasible = True
                    for p, _key, c2 in parts:
                        child = dp(c2, worker, next_used, next_hidden)
                        if not math.isfinite(child[0]):
                            feasible = False; break
                        total += p * child[0]; ea += p * child[1]; ee += p * child[2]; calls += p * child[3]
                    if feasible:
                        cand = (total, ea, ee, calls)
                        if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                            best = cand
        return best

    return dp(initial, initial, 0, 0)


def main():
    rng = random.Random(SEED)
    families = ["balanced", "high_overhead", "low_overhead", "mixed_backend", "nonbatchable"]
    worlds = [gen_world(rng.randrange(1_000_000_000), families[i % len(families)]) for i in range(WORLDS)]
    baseline = [exact_policy(w, None) for w in worlds]
    base_total = statistics.fmean(x[0] for x in baseline)
    base_calls = statistics.fmean(x[3] for x in baseline)
    base_exp = statistics.fmean(x[2] for x in baseline)

    rows = []
    for threshold in THRESHOLDS:
        vals = [exact_policy(w, threshold) for w in worlds]
        total = statistics.fmean(x[0] for x in vals)
        calls = statistics.fmean(x[3] for x in vals)
        exp = statistics.fmean(x[2] for x in vals)
        rows.append({
            "threshold": threshold,
            "total_cost_reduction_pct": 100 * (1 - total / base_total),
            "tool_call_reduction_pct": 100 * (1 - calls / base_calls),
            "worker_exposure_change_pct": 100 * (exp / base_exp - 1),
            "mean_total_cost": total,
            "mean_tool_calls": calls,
        })

    # Quality is exact by construction; choose maximum total-cost reduction, then calls.
    winner = max(rows, key=lambda r: (r["total_cost_reduction_pct"], r["tool_call_reduction_pct"]))
    result = {
        "experiment": "adaptive-batched-hidden-acquisition-development-v0.2",
        "status": "development_only",
        "worlds": WORLDS,
        "baseline_single_hidden": {"mean_total_cost": round(base_total, 6), "mean_tool_calls": round(base_calls, 6), "mean_worker_exposure": round(base_exp, 6)},
        "thresholds": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows],
        "selected": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in winner.items()},
        "quality_invariant": "All compared policies are exact DPs under the same controller + worker decision-sufficiency termination rule; thresholding only controls which backend-supported bundle actions exist.",
        "guardrail": "Development only. Freeze the selected threshold before adding new generator families or seed.",
        "claim_boundary": "Synthetic cost mechanics. Real adoption requires actual backend batching semantics and measured call overhead."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
