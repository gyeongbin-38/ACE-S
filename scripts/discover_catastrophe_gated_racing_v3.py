#!/usr/bin/env python3
"""Development v3: catastrophe-gated sequential rollout racing.

Prior tail-gated racing passed mean/p90/coverage gates but still had rare >50%
per-world regressions. This search adds a hard maximum-world degradation gate.
Quality First: compute savings are considered only after all four gates pass.

Development only. Freeze before any fresh sealed OOD generator/seed.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import asdict

from discover_sequential_rollout_racing import DEV_SEED, evaluate, policies
from run_context_action_dominance_bench import gen_world

WORLDS = 420
MEAN_GATE = 0.01
P90_GATE = 0.05
WITHIN_1_GATE = 0.95
MAX_WORLD_GATE = 0.20


def quantile(values, q):
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def main():
    rng = random.Random(DEV_SEED + 91_771)
    families = ["mixed", "light_redundancy", "heavy_redundancy", "costly_coarse"]
    worlds = [gen_world(rng.randrange(1_000_000_000), families[i % len(families)]) for i in range(WORLDS)]
    valid = []
    for i, world in enumerate(worlds):
        seed = DEV_SEED + 91_771 + i * 71
        be, bc = evaluate(world, seed, None)
        if math.isfinite(be) and math.isfinite(bc):
            valid.append((world, seed, be, bc))
    base_e = statistics.fmean(x[2] for x in valid)
    base_c = statistics.fmean(x[3] for x in valid)

    rows = []
    for policy in policies():
        envs, comps, deltas = [], [], []
        for world, seed, be, _bc in valid:
            e, c = evaluate(world, seed, policy)
            envs.append(e); comps.append(c); deltas.append(e / be - 1.0)
        mean_e = statistics.fmean(envs); mean_c = statistics.fmean(comps)
        mean_d = mean_e / base_e - 1.0
        p90 = quantile(deltas, .90); mx = max(deltas)
        within = sum(d <= .01 + 1e-12 for d in deltas) / len(deltas)
        comp_red = 1 - mean_c / base_c
        ok = mean_d <= MEAN_GATE and p90 <= P90_GATE and within >= WITHIN_1_GATE and mx <= MAX_WORLD_GATE
        rows.append((policy, ok, mean_d, p90, mx, within, comp_red, mean_e, mean_c))

    eligible = [r for r in rows if r[1]]
    eligible.sort(key=lambda r: (r[6], -r[4], r[5]), reverse=True)

    def compact(r):
        p, _ok, md, p90, mx, within, cr, me, mc = r
        return {"policy": asdict(p), "mean_environment_change_pct": round(100*md,3), "p90_world_change_pct": round(100*p90,3), "max_world_change_pct": round(100*mx,3), "within_1pct_world_rate_pct": round(100*within,3), "rollout_compute_reduction_pct": round(100*cr,3), "mean_environment_cost": round(me,6), "mean_rollout_samples": round(mc,3)}

    result = {
        "experiment": "catastrophe-gated-sequential-racing-development-v0.3",
        "status": "development_only",
        "worlds": len(valid),
        "candidate_policies": len(rows),
        "quality_gates": {"mean_max_pct":1.0,"p90_max_pct":5.0,"within_1pct_min_pct":95.0,"max_world_degradation_pct":20.0},
        "fixed_k8": {"mean_environment_cost":round(base_e,6),"mean_rollout_samples":round(base_c,3)},
        "eligible_policies": len(eligible),
        "selected": compact(eligible[0]) if eligible else None,
        "top_eligible": [compact(r) for r in eligible[:8]],
        "best_rejected_for_catastrophe_gate": [compact(r) for r in sorted([r for r in rows if r[2] <= MEAN_GATE and r[4] > MAX_WORLD_GATE], key=lambda r:r[6], reverse=True)[:5]],
        "guardrail": "Development only. If no policy survives, do not relax the catastrophe gate post hoc; redesign the estimator/controller instead.",
        "claim_boundary": "Synthetic controller economics; maximum-world degradation is a synthetic tail-risk guardrail, not an end-to-end answer-quality guarantee."
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
