#!/usr/bin/env python3
"""Development benchmark: selective worker exposure + batched controller acquisition.

Tests whether the tool-call increase seen in acquisition/exposure separation can be
mitigated by batching compatible structured actions from the same backend.

Both conditions track controller and worker-visible epistemic state separately and
terminate only when both are decision-sufficient. The only difference is whether
pairs of unacquired structured actions from the same batch-capable backend may be
acquired in one call with shared call overhead.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

SEED = 9_210_331
WORLDS = 220


class World:
    def __init__(self, priors, decisions, actions, family):
        self.priors = tuple(priors); self.decisions = tuple(decisions)
        self.actions = actions; self.family = family; self.n = len(priors)
    def mass(self, subset): return sum(self.priors[i] for i in subset)
    def solved(self, subset): return len({self.decisions[i] for i in subset}) <= 1


def action_outcome(action, world_index): return action["outcomes"][world_index]


def narrow(subset, action, outcome):
    return tuple(i for i in subset if action_outcome(action, i) == outcome)


def partitions(world, subset, action_indices):
    groups = defaultdict(list)
    for i in subset:
        key = tuple(action_outcome(world.actions[a], i) for a in action_indices)
        groups[key].append(i)
    z = world.mass(subset)
    return [(world.mass(tuple(g))/z, key, tuple(sorted(g))) for key, g in groups.items()]


def acquisition_cost(action): return action["call_overhead"] + action["payload_cost"]


def bundle_cost(a, b):
    # same backend guaranteed by candidate generator; one shared call overhead and
    # both payload costs. No artificial payload discount.
    return max(a["call_overhead"], b["call_overhead"]) + a["payload_cost"] + b["payload_cost"]


def decoupled_exact(world, allow_bundles):
    n = len(world.actions)
    initial = tuple(range(world.n))

    @functools.lru_cache(None)
    def dp(controller, worker, used_mask, hidden_mask):
        if world.solved(controller) and world.solved(worker):
            return 0.0, 0.0, 0.0, 0.0
        best = (math.inf, math.inf, math.inf, math.inf)  # total, acq, exposure, calls

        # Expose one previously hidden structured result.
        for idx in range(n):
            if not (hidden_mask & (1 << idx)): continue
            action = world.actions[idx]
            outcomes = {action_outcome(action, i) for i in controller}
            if len(outcomes) != 1: continue
            obs = next(iter(outcomes))
            w2 = narrow(worker, action, obs)
            if w2 == worker: continue
            child = dp(controller, w2, used_mask, hidden_mask & ~(1 << idx))
            exp = action["exposure_cost"]
            cand = (exp + child[0], child[1], exp + child[2], child[3])
            if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]): best = cand

        # Single acquisitions.
        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx): continue
            parts = partitions(world, controller, (idx,))
            known = len(parts) == 1
            if known and action["kind"] != "semantic": continue
            if known:
                obs = parts[0][1][0]
                w2 = narrow(worker, action, obs)
                if w2 == worker: continue
                child = dp(controller, w2, used_mask | (1 << idx), hidden_mask)
                acq = acquisition_cost(action); exp = action["exposure_cost"]
                cand = (acq+exp+child[0], acq+child[1], exp+child[2], 1+child[3])
                if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]): best = cand
                continue
            acq = acquisition_cost(action)
            exp = action["exposure_cost"] if action["kind"] == "semantic" else 0.0
            total, ea, ee, calls = acq+exp, acq, exp, 1.0
            next_used = used_mask | (1 << idx)
            next_hidden = hidden_mask | (1 << idx) if action["kind"] == "structured" else hidden_mask
            feasible = True
            for p, key, c2 in parts:
                w2 = worker
                if action["kind"] == "semantic": w2 = narrow(worker, action, key[0])
                child = dp(c2, w2, next_used, next_hidden)
                if not math.isfinite(child[0]): feasible=False; break
                total += p*child[0]; ea += p*child[1]; ee += p*child[2]; calls += p*child[3]
            if feasible:
                cand=(total,ea,ee,calls)
                if (cand[0],cand[2],cand[3]) < (best[0],best[2],best[3]): best=cand

        # Pair bundles: structured only, same batch-capable backend.
        if allow_bundles:
            candidates = [i for i,a in enumerate(world.actions) if not (used_mask & (1<<i)) and a["kind"]=="structured" and a["batchable"]]
            for pos, i in enumerate(candidates):
                ai = world.actions[i]
                for j in candidates[pos+1:]:
                    aj = world.actions[j]
                    if ai["backend"] != aj["backend"]: continue
                    parts = partitions(world, controller, (i,j))
                    if len(parts) <= 1: continue
                    acq = bundle_cost(ai,aj)
                    total, ea, ee, calls = acq, acq, 0.0, 1.0
                    next_used = used_mask | (1<<i) | (1<<j)
                    next_hidden = hidden_mask | (1<<i) | (1<<j)
                    feasible=True
                    for p,_key,c2 in parts:
                        child=dp(c2,worker,next_used,next_hidden)
                        if not math.isfinite(child[0]): feasible=False; break
                        total += p*child[0]; ea += p*child[1]; ee += p*child[2]; calls += p*child[3]
                    if feasible:
                        cand=(total,ea,ee,calls)
                        if (cand[0],cand[2],cand[3]) < (best[0],best[2],best[3]): best=cand
        return best
    return dp(initial,initial,0,0)


def random_partition(rng,n,k):
    x=[rng.randrange(k) for _ in range(n)]
    if len(set(x))<2: x[0],x[-1]=0,1
    return tuple(x)


def gen_world(seed,family):
    rng=random.Random(seed); n=rng.randint(5,7); dcount=rng.choice([2,2,3])
    decisions=[rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount): decisions[d%n]=d
    raw=[rng.gammavariate(rng.uniform(.4,2.1),1.0) for _ in range(n)]; z=sum(raw); priors=[x/z for x in raw]
    if family=="high_overhead": overhead=(2.0,5.0)
    elif family=="low_overhead": overhead=(0.1,0.6)
    elif family=="mixed_backend": overhead=(0.8,3.0)
    else: overhead=(0.6,2.5)
    actions=[]; backends=["repo","files","search"]
    for _ in range(rng.randint(6,8)):
        structured=rng.random()<0.65
        backend=rng.choice(backends)
        actions.append({
            "kind":"structured" if structured else "semantic",
            "backend":backend,
            "batchable": structured and (family!="nonbatchable") and rng.random()<0.85,
            "outcomes":random_partition(rng,n,rng.choice([2,3,4])),
            "call_overhead":rng.uniform(*overhead),
            "payload_cost":rng.uniform(.15,1.4),
            "exposure_cost":rng.uniform(2.0,10.0)*(1.15 if structured else 1.0),
        })
    # Direct semantic proof path.
    actions.append({"kind":"semantic","backend":"worker","batchable":False,"outcomes":tuple(decisions),"call_overhead":rng.uniform(*overhead),"payload_cost":rng.uniform(.4,1.2),"exposure_cost":rng.uniform(2.0,7.0)})
    return World(priors,decisions,actions,family)


def summary(vals):
    vals=sorted(vals); p90=vals[int(.9*(len(vals)-1))]
    return {"mean":round(statistics.fmean(vals),6),"median":round(statistics.median(vals),6),"p90":round(p90,6)}


def main():
    rng=random.Random(SEED); families=["balanced","high_overhead","low_overhead","mixed_backend","nonbatchable"]
    singles=[]; bundles=[]; s_calls=[]; b_calls=[]; s_exp=[]; b_exp=[]; by=defaultdict(lambda:{"total":[],"calls":[]})
    for i in range(WORLDS):
        fam=families[i%len(families)]; w=gen_world(rng.randrange(1_000_000_000),fam)
        a=decoupled_exact(w,False); b=decoupled_exact(w,True)
        if not all(math.isfinite(x) for x in (*a,*b)): continue
        singles.append(a[0]); bundles.append(b[0]); s_calls.append(a[3]); b_calls.append(b[3]); s_exp.append(a[2]); b_exp.append(b[2])
        by[fam]["total"].append(b[0]/a[0]); by[fam]["calls"].append(b[3]/a[3] if a[3]>0 else 1.0)
    result={
        "experiment":"batched-hidden-acquisition-development-v0.1",
        "status":"development_only",
        "worlds":len(singles),
        "single_hidden_acquisition":{"total_cost":summary(singles),"tool_calls":summary(s_calls),"worker_exposure":summary(s_exp)},
        "batched_hidden_acquisition":{"total_cost":summary(bundles),"tool_calls":summary(b_calls),"worker_exposure":summary(b_exp)},
        "mean_total_cost_reduction_pct":round(100*(1-statistics.fmean(bundles)/statistics.fmean(singles)),3),
        "mean_tool_call_reduction_pct":round(100*(1-statistics.fmean(b_calls)/statistics.fmean(s_calls)),3),
        "mean_worker_exposure_change_pct":round(100*(statistics.fmean(b_exp)/statistics.fmean(s_exp)-1),3),
        "by_family":{f:{"total_cost_reduction_pct":round(100*(1-statistics.fmean(d["total"])),3),"tool_call_reduction_pct":round(100*(1-statistics.fmean(d["calls"])),3)} for f,d in by.items()},
        "quality_invariant":"Both exact policies track controller and worker-visible epistemic state separately and terminate only when both are decision-sufficient. Bundles change acquisition economics only; hidden structured evidence still must be selectively exposed or replaced before answer termination.",
        "claim_boundary":"Synthetic mechanics with explicit batch-capable backend contracts. Real tool APIs must actually support equivalent batched retrieval semantics and measured shared overhead."
    }
    print(json.dumps(result,indent=2))


if __name__=="__main__": main()
