#!/usr/bin/env python3
"""Sealed OOD test for frozen selective-retention lookahead v0.3.

IMPORTANT: the trigger below is copied from the freeze artifact and must not be
modified after this file introduces the new seed/families.
Synthetic lifecycle economics only; not end-to-end LLM evidence.
"""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict

import discover_retention_scheduler as ret
from discover_retention_lookahead_depth import NOISE_SEEDS, SIGMAS, rollout_cost

FREEZE_COMMIT = "72609b377213a6992c32065a9c10a627528e129e"
SEALED_SEED = 271_904_663
ITEMS_PER_FAMILY = 60
FAMILIES = (
    "paired_after_plateau",
    "weak_weak_strong_revival",
    "semantic_then_exact_revivals",
    "irregular_alternating_bursts",
    "cost_inversion_multi_return",
    "steady_moderate_negative",
)

# Frozen v0.3 trigger. Do not tune on sealed outcomes.
QUIET_THRESHOLD = 0.09
REVIVAL_THRESHOLD = 0.18
MIN_QUIET_STEPS = 2
MIN_REVIVAL_SEGMENTS = 3
PRESSURE_THRESHOLD = 6.0
MIN_SEMANTIC_AMBIGUITY = 0.60


def segment_count(values, threshold):
    count = 0
    active = False
    for value in values:
        now = value >= threshold
        if now and not active:
            count += 1
        active = now
    return count


def fires(item: ret.Item) -> bool:
    p = item.p_need
    best = None
    for cut in range(MIN_QUIET_STEPS, len(p) - 1):
        if max(p[cut-MIN_QUIET_STEPS:cut]) > QUIET_THRESHOLD:
            continue
        future = p[cut:]
        future_need = sum(future)
        if future_need <= 1e-12:
            continue
        exact_mass = sum(pn * pe for pn, pe in zip(future, item.p_exact[cut:]))
        exact_rate = exact_mass / future_need
        ambiguity = 4.0 * exact_rate * (1.0 - exact_rate)
        pressure = item.reacquire_cost * (future_need + 0.75 * exact_mass)
        pressure /= max(item.raw_hold * max(1, len(future)) + item.compact_cost, 1e-12)
        revivals = segment_count(future, REVIVAL_THRESHOLD)
        feature = (revivals, pressure, ambiguity)
        if best is None or feature > best:
            best = feature
    revivals, pressure, ambiguity = best or (0, 0.0, 0.0)
    return (
        (revivals >= MIN_REVIVAL_SEGMENTS and pressure >= 0.65 * PRESSURE_THRESHOLD)
        or (pressure >= PRESSURE_THRESHOLD and ambiguity >= MIN_SEMANTIC_AMBIGUITY)
    )


def clamp(x, lo=0.01, hi=0.98):
    return min(hi, max(lo, x))


def make_item(rng: random.Random, family: str) -> ret.Item:
    # All families below were introduced after v0.3 freeze.
    if family == "paired_after_plateau":
        p_need = [rng.uniform(.35,.65), rng.uniform(.22,.45), rng.uniform(.01,.05), rng.uniform(.01,.05),
                  rng.uniform(.42,.72), rng.uniform(.02,.08), rng.uniform(.42,.72), rng.uniform(.02,.08)]
        p_exact = [rng.uniform(.20,.55) for _ in p_need]
    elif family == "weak_weak_strong_revival":
        p_need = [rng.uniform(.28,.52), rng.uniform(.01,.05), rng.uniform(.16,.27), rng.uniform(.02,.07),
                  rng.uniform(.16,.27), rng.uniform(.02,.07), rng.uniform(.55,.82), rng.uniform(.02,.08), rng.uniform(.25,.48)]
        p_exact = [rng.uniform(.15,.55) for _ in p_need]
    elif family == "semantic_then_exact_revivals":
        p_need = [rng.uniform(.35,.60), rng.uniform(.01,.05), rng.uniform(.45,.72), rng.uniform(.02,.06),
                  rng.uniform(.42,.68), rng.uniform(.02,.06), rng.uniform(.45,.75)]
        p_exact = [rng.uniform(.12,.30), rng.uniform(.12,.30), rng.uniform(.12,.28), rng.uniform(.15,.35),
                   rng.uniform(.62,.88), rng.uniform(.65,.90), rng.uniform(.72,.94)]
    elif family == "irregular_alternating_bursts":
        horizon = 10
        p_need=[]
        for t in range(horizon):
            if t in (0,3,6,9): p_need.append(rng.uniform(.42,.78))
            elif t in (1,4,7): p_need.append(rng.uniform(.01,.06))
            else: p_need.append(rng.uniform(.08,.20))
        p_exact=[rng.uniform(.18,.68) for _ in p_need]
    elif family == "cost_inversion_multi_return":
        p_need = [rng.uniform(.20,.40), rng.uniform(.01,.05), rng.uniform(.36,.62), rng.uniform(.02,.07),
                  rng.uniform(.38,.68), rng.uniform(.02,.07), rng.uniform(.40,.72), rng.uniform(.10,.22)]
        p_exact=[rng.uniform(.20,.62) for _ in p_need]
    else:  # steady_moderate_negative: no quiet gap; should usually remain depth1.
        p_need=[rng.uniform(.20,.46) for _ in range(rng.randint(7,10))]
        p_exact=[rng.uniform(.20,.68) for _ in p_need]

    raw_hold = rng.uniform(.18,.72)
    abstract_hold = raw_hold * rng.uniform(.08,.30)
    reacquire = rng.uniform(2.0,8.5)
    compact = rng.uniform(.15,1.25)
    failure = rng.uniform(.04,.24)
    if family == "cost_inversion_multi_return":
        reacquire *= rng.uniform(1.6,2.8)
        raw_hold *= rng.uniform(1.25,2.0)
    return ret.Item(tuple(map(clamp,p_need)), tuple(map(clamp,p_exact)), raw_hold, abstract_hold, reacquire, compact, failure, family)


def mean(xs): return statistics.fmean(xs)


def main():
    rng=random.Random(SEALED_SEED)
    items=[]; iid=0
    for family in FAMILIES:
        for _ in range(ITEMS_PER_FAMILY):
            item=make_item(rng,family)
            items.append((iid,item,ret.optimal_cost(item),family))
            iid+=1

    selected_ids={iid for iid,item,_opt,_family in items if fires(item)}
    d1=[]; d3=[]; sel=[]
    by=defaultdict(lambda:{"d1":[],"d3":[],"sel":[],"ids":set()})
    for sigma in SIGMAS:
        for nseed in NOISE_SEEDS:
            for iid,item,opt,family in items:
                a=rollout_cost(item,iid,sigma,nseed,1)/opt
                b=rollout_cost(item,iid,sigma,nseed,3)/opt
                s=b if iid in selected_ids else a
                d1.append(a); d3.append(b); sel.append(s)
                by[family]["d1"].append(a); by[family]["d3"].append(b); by[family]["sel"].append(s); by[family]["ids"].add(iid)

    full_gain=mean(d1)-mean(d3)
    sel_gain=mean(d1)-mean(sel)
    capture=sel_gain/full_gain if full_gain>1e-12 else 0.0
    neg="steady_moderate_negative"
    neg_ids=by[neg]["ids"]
    neg_rate=len(neg_ids & selected_ids)/len(neg_ids)
    result={
      "experiment":"selective-retention-lookahead-v3-sealed-ood-v0.1",
      "status":"sealed_after_freeze",
      "freeze_commit":FREEZE_COMMIT,
      "sealed_seed":SEALED_SEED,
      "families":FAMILIES,
      "items":len(items),
      "evaluations_per_condition":len(d1),
      "always_depth1_mean":round(mean(d1),6),
      "always_depth3_mean":round(mean(d3),6),
      "selective_mean":round(mean(sel),6),
      "depth3_item_rate_pct":round(100*len(selected_ids)/len(items),3),
      "mean_cost_reduction_vs_depth1_pct":round(100*sel_gain/mean(d1),3),
      "fraction_of_always_depth3_gain_captured_pct":round(100*capture,3),
      "negative_control_depth3_rate_pct":round(100*neg_rate,3),
      "by_family":{f:{
          "items":len(v["ids"]),
          "depth3_item_rate_pct":round(100*len(v["ids"] & selected_ids)/len(v["ids"]),3),
          "depth1_mean":round(mean(v["d1"]),5),
          "depth3_mean":round(mean(v["d3"]),5),
          "selective_mean":round(mean(v["sel"]),5),
      } for f,v in sorted(by.items())},
      "sealed_gate":{
          "beats_always_depth1":mean(sel)<mean(d1),
          "captures_at_least_75pct_depth3_gain":capture>=.75,
          "depth3_item_rate_le_40pct":len(selected_ids)/len(items)<=.40,
          "negative_control_depth3_rate_le_15pct":neg_rate<=.15,
      },
      "claim_boundary":"Frozen trigger on post-freeze synthetic lifecycle families/seed. Generator-level future probabilities are visible to the trigger; production requires calibrated estimates. Not end-to-end LLM quality evidence."
    }
    result["passed_predeclared_all_gate"]=all(result["sealed_gate"].values())
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
