#!/usr/bin/env python3
"""Audit whether rollout sample count is a faithful compute proxy.

The current synthetic rollout evaluators memoize base-policy continuation values.
Repeated rollout samples can therefore hit a cached successor value rather than
incur a new continuation evaluation. This audit reports both sample draws and
unique base-value cache misses. It does not change any policy.
"""
from __future__ import annotations

import functools, json, math, random, statistics

from discover_adaptive_rollout_budget_v2 import DEV_SEED, base_policy_cost, choose_action
from run_context_action_dominance_bench import gen_world, partitions

WORLDS=320


def evaluate_with_accounting(world, seed):
    base=base_policy_cost(world,seed)
    initial=tuple(range(world.n))
    @functools.lru_cache(None)
    def rec(subset):
        if world.solved(subset): return 0.0,0.0
        action,samples=choose_action(world,subset,seed,base,None)
        if action is None: return math.inf,math.inf
        parts=list(partitions(world,subset,action))
        pself=sum(p for p,st in parts if st==subset)
        if pself>=1-1e-12: return math.inf,math.inf
        env=world.actions[action]["cost"]; draws=float(samples)
        for p,st in parts:
            if st==subset: continue
            e,d=rec(st); env+=p*e; draws+=p*d
        return env/(1-pself),draws/(1-pself)
    env,draws=rec(initial)
    info=base.cache_info()
    return env,draws,float(info.misses),float(info.hits)


def main():
    rng=random.Random(991_447_203)
    fams=["mixed","light_redundancy","heavy_redundancy","costly_coarse"]
    rows=[]
    for i in range(WORLDS):
        w=gen_world(rng.randrange(1_000_000_000),fams[i%4])
        row=evaluate_with_accounting(w,991_447_203+i*43)
        if all(math.isfinite(x) for x in row): rows.append((fams[i%4],*row))
    draws=[r[2] for r in rows]; misses=[r[3] for r in rows]; hits=[r[4] for r in rows]
    ratios=[m/d if d>0 else 0.0 for d,m in zip(draws,misses)]
    by={}
    for fam in fams:
        rs=[r for r in rows if r[0]==fam]
        ds=[r[2] for r in rs]; ms=[r[3] for r in rs]
        by[fam]={"mean_sample_draws":round(statistics.fmean(ds),3),"mean_unique_base_value_evaluations":round(statistics.fmean(ms),3),"unique_eval_to_draw_ratio_pct":round(100*statistics.fmean(m/d if d>0 else 0 for d,m in zip(ds,ms)),3)}
    result={
      "experiment":"rollout-compute-accounting-audit-v0.1",
      "status":"measurement_audit",
      "worlds":len(rows),
      "mean_rollout_sample_draws":round(statistics.fmean(draws),3),
      "mean_unique_base_value_evaluations":round(statistics.fmean(misses),3),
      "mean_base_cache_hits":round(statistics.fmean(hits),3),
      "mean_unique_eval_to_sample_draw_ratio_pct":round(100*statistics.fmean(ratios),3),
      "by_family":by,
      "interpretation":"Rollout sample draws are an algorithmic budget proxy, not a direct wall-clock or expensive-model-call metric when continuation values are memoized. Public compute claims should report both draws and unique/cache-aware evaluations, and ultimately measured latency.",
      "claim_boundary":"Synthetic accounting audit only. Cache misses include recursive base-policy state evaluation and are still not equivalent to real LLM calls."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
