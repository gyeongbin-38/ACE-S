#!/usr/bin/env python3
"""Development v3: catastrophic-tail-safe sequential rollout racing.

V2 showed that mean/P90 gates can hide rare ~50% environment-cost regressions.
V3 therefore treats tail safety as a hard constraint before compute savings:

- mean degradation <= +0.5%
- p95 per-world degradation <= +1%
- >=97% worlds within +1%
- worst single-world degradation <= +10%
- CVaR95 (mean worst 5%) <= +3%

This is development-only. If no policy passes, the correct result is to retain
fixed K=8 rather than relax Quality-First gates.
"""
from __future__ import annotations

import json, math, random, statistics
from dataclasses import asdict

from discover_sequential_rollout_racing import RacingPolicy, evaluate
from run_context_action_dominance_bench import gen_world

DEV_SEED=184_773_901
WORLDS=480
MEAN_GATE=.005
P95_GATE=.01
WITHIN1_GATE=.97
MAX_GATE=.10
CVAR95_GATE=.03


def quantile(vals,q):
    xs=sorted(vals); p=(len(xs)-1)*q; lo=math.floor(p); hi=math.ceil(p)
    return xs[lo] if lo==hi else xs[lo]*(hi-p)+xs[hi]*(p-lo)


def cvar_upper(vals, frac=.05):
    xs=sorted(vals, reverse=True)
    n=max(1, math.ceil(len(xs)*frac))
    return statistics.fmean(xs[:n])


def policies():
    # V2's catastrophic errors all came from early commitments. Explore later
    # minimum rounds and more conservative interval separation, while retaining
    # K=8 as the hard upper budget through the shared evaluator.
    for rounds in (4,5,6,7):
        for z in (.75,1.0,1.5,2.0,2.5,3.0):
            for gap in (0.0,.02,.05,.10,.20):
                yield RacingPolicy(rounds,z,gap)


def main():
    rng=random.Random(DEV_SEED)
    families=["mixed","light_redundancy","heavy_redundancy","costly_coarse"]
    worlds=[gen_world(rng.randrange(1_000_000_000),families[i%len(families)]) for i in range(WORLDS)]
    valid=[]
    for i,w in enumerate(worlds):
        seed=DEV_SEED+i*101
        be,bc=evaluate(w,seed,None)
        if math.isfinite(be) and math.isfinite(bc): valid.append((i,w,seed,be,bc))
    base_e=statistics.fmean(x[3] for x in valid); base_c=statistics.fmean(x[4] for x in valid)

    rows=[]
    for p in policies():
        envs=[]; comps=[]; deltas=[]
        for _i,w,seed,be,_bc in valid:
            e,c=evaluate(w,seed,p); envs.append(e); comps.append(c); deltas.append(e/be-1)
        me=statistics.fmean(envs); mc=statistics.fmean(comps)
        mean_delta=me/base_e-1; p95=quantile(deltas,.95); within=sum(d<=.01+1e-12 for d in deltas)/len(deltas)
        mx=max(deltas); cv=cvar_upper(deltas,.05); reduction=1-mc/base_c
        ok=(mean_delta<=MEAN_GATE+1e-12 and p95<=P95_GATE+1e-12 and within>=WITHIN1_GATE-1e-12 and mx<=MAX_GATE+1e-12 and cv<=CVAR95_GATE+1e-12)
        rows.append((p,ok,mean_delta,p95,within,mx,cv,reduction,me,mc))
    eligible=[r for r in rows if r[1] and r[7]>0]
    eligible.sort(key=lambda r:(r[7],-r[6],-r[5]),reverse=True)

    def compact(r):
        p,_ok,md,p95,w,mx,cv,red,me,mc=r
        return {"policy":asdict(p),"mean_environment_change_pct":round(100*md,3),"p95_world_change_pct":round(100*p95,3),"within_1pct_world_rate_pct":round(100*w,3),"max_world_change_pct":round(100*mx,3),"cvar95_world_change_pct":round(100*cv,3),"rollout_compute_reduction_pct":round(100*red,3),"mean_environment_cost":round(me,6),"mean_rollout_samples":round(mc,3)}

    result={
      "experiment":"sequential-rollout-racing-development-v0.3-catastrophic-tail-gated",
      "status":"development_only",
      "worlds":len(valid),"candidate_policies":len(rows),
      "quality_gates":{"mean_degradation_max_pct":.5,"p95_world_degradation_max_pct":1.0,"within_1pct_world_rate_min_pct":97.0,"max_world_degradation_max_pct":10.0,"cvar95_degradation_max_pct":3.0},
      "fixed_k8":{"mean_environment_cost":round(base_e,6),"mean_rollout_samples":round(base_c,3)},
      "eligible_policies":len(eligible),
      "selected":compact(eligible[0]) if eligible else None,
      "top_eligible":[compact(r) for r in eligible[:10]],
      "best_compute_rejected":[compact(r) for r in sorted([x for x in rows if x[7]>0 and not x[1]],key=lambda r:r[7],reverse=True)[:5]],
      "guardrail":"Quality gates were defined after observing v2's catastrophic tail but before this fresh development seed was run. If no policy passes, retain fixed K=8. Freeze any passing policy before new OOD families/seed.",
      "claim_boundary":"Synthetic controller rollout economics; empirical intervals are not formal confidence guarantees and do not establish end-to-end LLM quality equivalence."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
