#!/usr/bin/env python3
"""Strict negative-control regression for frozen cost-floor pruning.

This corrects a benchmark-construction flaw in the earlier sealed suite: random
binary partitions in nominal "no bound" families could accidentally be
one-step decision-sufficient. Here worlds are rejected unless *no single useful
action* solves every resulting branch at the initial state.

The frozen pruning algorithm is unchanged. This is a benchmark-fixture repair,
not a new sealed claim about a tuned policy.
"""
from __future__ import annotations

import json
import math
import random
import statistics

from run_context_action_dominance_bench import World, exact_dp, partitions, useful_actions
from run_cost_floor_pruning_bench import dynamic_combined_prune, exact_dp_with_pruner

SEED = 144_907_331
TARGET_WORLDS = 300


def normalize(xs):
    z=sum(xs); return [x/z for x in xs]


def one_step_complete(world, subset, action):
    parts=list(partitions(world, subset, action))
    return bool(parts) and all(world.solved(state) for _p,state in parts)


def make_candidate(rng):
    n=8
    # XOR decision cannot be solved by either source bit alone.
    decisions=tuple((((i>>0)&1)^((i>>1)&1)) for i in range(n))
    priors=normalize([rng.uniform(.2,1.8) for _ in range(n)])
    actions=[]
    bit0=tuple((i>>0)&1 for i in range(n))
    bit1=tuple((i>>1)&1 for i in range(n))
    bit2=tuple((i>>2)&1 for i in range(n))
    for outcomes in (bit0,bit1,bit2):
        actions.append({"cost":rng.uniform(.35,1.1),"outcomes":outcomes})
    # Only add duplicates/coarsenings of source bits; never arbitrary random
    # partitions that can accidentally encode the XOR decision in one step.
    for _ in range(rng.randint(4,9)):
        base=rng.choice((bit0,bit1,bit2))
        if rng.random()<.5:
            outcomes=base
        else:
            # Coarsen by collapsing all observations to one value (not useful),
            # or keep the bit exactly. This cannot become more informative.
            outcomes=tuple(0 for _ in range(n)) if rng.random()<.35 else base
        actions.append({"cost":rng.uniform(.5,3.0),"outcomes":outcomes})
    return World(priors,decisions,actions,"strict_no_upper")


def main():
    rng=random.Random(SEED)
    worlds=[]; attempts=0
    while len(worlds)<TARGET_WORLDS and attempts<TARGET_WORLDS*20:
        attempts+=1
        w=make_candidate(rng)
        initial=tuple(range(w.n))
        useful=useful_actions(w,initial)
        if any(one_step_complete(w,initial,a) for a in useful):
            continue
        if not math.isfinite(exact_dp(w)(initial)):
            continue
        worlds.append(w)

    bound_rates=[]; reductions=[]; exact=[]
    for w in worlds:
        initial=tuple(range(w.n))
        useful=useful_actions(w,initial)
        keep,_dom,_bounded,upper=dynamic_combined_prune(w,initial)
        bound_rates.append(float(math.isfinite(upper)))
        reductions.append(1-len(keep)/len(useful))
        optimum=exact_dp(w)(initial)
        pruned=exact_dp_with_pruner(w,lambda ww,s: dynamic_combined_prune(ww,s)[0])(initial)
        exact.append(float(abs(pruned-optimum)<=1e-9))

    result={
      "experiment":"cost-floor-strict-no-upper-abstention-regression-v0.1",
      "status":"benchmark_fixture_repair",
      "worlds":len(worlds),
      "generator_attempts":attempts,
      "verified_one_step_complete_action_rate_pct":0.0,
      "reported_initial_upper_bound_available_pct":round(100*statistics.fmean(bound_rates),3),
      "exact_optimal_preservation_pct":round(100*statistics.fmean(exact),3),
      "mean_combined_candidate_reduction_pct":round(100*statistics.fmean(reductions),3),
      "passed_strict_abstention":sum(bound_rates)==0,
      "claim_boundary":"Fixture repair for the frozen cost-floor algorithm. Worlds are construction-validated to have no one-step complete action. This does not replace the original sealed OOD result; it diagnoses its nominal no-bound control."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
