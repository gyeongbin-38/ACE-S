#!/usr/bin/env python3
"""Development interaction test: typed certificates + exact frontier pruning.

Question: when certificate-capable actions change the legal worker-exposure cost,
do structural dominance and cost-floor pruning still preserve the exact optimum,
and does the combined stack retain an efficiency benefit versus full exposure?

Synthetic finite decision mechanics only. Development before freeze.
"""
from __future__ import annotations

import functools, json, math, random, statistics
from collections import defaultdict

SEED=491_208_773
WORLDS=360
CERT_FRAC=.75
VALIDATION_FRAC=.15


class World:
    def __init__(self,priors,decisions,actions,family):
        self.priors=tuple(priors); self.decisions=tuple(decisions); self.actions=actions; self.family=family; self.n=len(priors)
    def mass(self,s): return sum(self.priors[i] for i in s)
    def solved(self,s): return len({self.decisions[i] for i in s})<=1


def partitions(w,subset,a):
    groups=defaultdict(list); out=w.actions[a]["outcomes"]
    for i in subset: groups[out[i]].append(i)
    z=w.mass(subset)
    for g in groups.values():
        st=tuple(sorted(g)); yield w.mass(st)/z,st


def useful(w,s): return [a for a in range(len(w.actions)) if len(list(partitions(w,s,a)))>1]


def full_cost(a): return a["acq"]+a["exposure"]

def cert_cost(a):
    if a["kind"]=="structured" and a["certificate_capable"]:
        return a["acq"] + CERT_FRAC*a["exposure"] + VALIDATION_FRAC*a["acq"]
    return full_cost(a)


def refines(w,s,b,a):
    bo=w.actions[b]["outcomes"]; ao=w.actions[a]["outcomes"]; groups=defaultdict(list)
    for i in s: groups[bo[i]].append(i)
    return all(len({ao[i] for i in g})<=1 for g in groups.values())


def dominance_keep(w,s,costfn):
    acts=useful(w,s); keep=[]
    for a in acts:
        dominated=False
        for b in acts:
            if a==b: continue
            ca=costfn(w.actions[a]); cb=costfn(w.actions[b])
            if cb<=ca+1e-12 and refines(w,s,b,a):
                if cb<ca-1e-12 or not refines(w,s,a,b) or b<a:
                    dominated=True; break
        if not dominated: keep.append(a)
    return keep


def one_step_complete(w,s,a): return all(w.solved(st) for _p,st in partitions(w,s,a))


def combined_keep(w,s,costfn):
    dom=dominance_keep(w,s,costfn)
    complete=[a for a in dom if one_step_complete(w,s,a)]
    if not complete: return dom,math.inf
    upper=min(costfn(w.actions[a]) for a in complete)
    # Immediate action cost is a valid lower bound on any plan beginning with a.
    return [a for a in dom if costfn(w.actions[a])<=upper+1e-12],upper


def exact_dp(w,costfn,pruner=None):
    @functools.lru_cache(None)
    def dp(s):
        if w.solved(s): return 0.0
        acts=pruner(w,s,costfn)[0] if pruner else useful(w,s)
        best=math.inf
        for a in acts:
            ps=list(partitions(w,s,a)); selfp=sum(p for p,st in ps if st==s)
            if selfp>=1-1e-12: continue
            rest=sum(p*dp(st) for p,st in ps if st!=s)
            q=(costfn(w.actions[a])+rest)/(1-selfp)
            best=min(best,q)
        return best
    return dp


def norm(xs): z=sum(xs); return [x/z for x in xs]

def part(rng,n,k):
    o=[rng.randrange(k) for _ in range(n)]
    if len(set(o))<2: o[0],o[-1]=0,1
    return tuple(o)


def make_world(seed,fam):
    rng=random.Random(seed); n=rng.randint(5,8); dc=rng.choice([2,2,3]); dec=[rng.randrange(dc) for _ in range(n)]
    for d in range(dc): dec[d%n]=d
    pri=norm([rng.gammavariate(rng.uniform(.4,2),1) for _ in range(n)])
    actions=[]
    for i in range(rng.randint(7,11)):
        structured=rng.random() < ({"cert_sparse":.35,"cert_dense":.85,"mixed":.6,"high_redundancy":.7}[fam])
        actions.append({
          "outcomes":part(rng,n,rng.choice([2,2,3,4])),
          "acq":math.exp(rng.uniform(math.log(.25),math.log(3.2))),
          "exposure":math.exp(rng.uniform(math.log(1.5),math.log(11.0))),
          "kind":"structured" if structured else "semantic",
          "certificate_capable":bool(structured and rng.random()<.75),
        })
    # Feasible full decision action.
    structured=fam!="cert_sparse"
    actions.append({"outcomes":tuple(dec),"acq":rng.uniform(.7,2.4),"exposure":rng.uniform(3.0,10.0),"kind":"structured" if structured else "semantic","certificate_capable":bool(structured)})
    if fam=="high_redundancy":
        for _ in range(8):
            src=actions[rng.randrange(len(actions))].copy(); src["acq"]*=rng.uniform(1.05,1.8); src["exposure"]*=rng.uniform(1.02,1.5); actions.append(src)
    return World(pri,dec,actions,fam)


def main():
    rng=random.Random(SEED); fams=("cert_sparse","cert_dense","mixed","high_redundancy")
    rows=[]; by=defaultdict(list)
    for i in range(WORLDS):
        fam=fams[i%len(fams)]; w=make_world(rng.randrange(1_000_000_000),fam); init=tuple(range(w.n))
        baseline=exact_dp(w,full_cost)(init)
        cert_unpruned=exact_dp(w,cert_cost)(init)
        cert_pruned=exact_dp(w,cert_cost,combined_keep)(init)
        if not all(math.isfinite(x) for x in (baseline,cert_unpruned,cert_pruned)): continue
        useful0=len(useful(w,init)); keep0=len(combined_keep(w,init,cert_cost)[0])
        row={"family":fam,"baseline":baseline,"cert_unpruned":cert_unpruned,"cert_pruned":cert_pruned,"reduction":1-keep0/useful0,"exact":abs(cert_unpruned-cert_pruned)<=1e-9}
        rows.append(row); by[fam].append(row)
    result={
      "experiment":"certificate-frontier-composition-development-v0.1",
      "status":"development_only",
      "worlds":len(rows),
      "certificate_fraction":CERT_FRAC,
      "validation_fraction":VALIDATION_FRAC,
      "pruned_exact_optimum_preservation_pct":round(100*statistics.fmean(float(r["exact"]) for r in rows),3),
      "mean_candidate_reduction_pct":round(100*statistics.fmean(r["reduction"] for r in rows),3),
      "mean_total_cost_reduction_vs_full_exposure_pct":round(100*(1-statistics.fmean(r["cert_pruned"] for r in rows)/statistics.fmean(r["baseline"] for r in rows)),3),
      "mean_certificate_only_cost_reduction_pct":round(100*(1-statistics.fmean(r["cert_unpruned"] for r in rows)/statistics.fmean(r["baseline"] for r in rows)),3),
      "by_family":{f:{
        "n":len(v),
        "exact_preservation_pct":round(100*statistics.fmean(float(r["exact"]) for r in v),3),
        "candidate_reduction_pct":round(100*statistics.fmean(r["reduction"] for r in v),3),
        "total_cost_reduction_pct":round(100*(1-statistics.fmean(r["cert_pruned"] for r in v)/statistics.fmean(r["baseline"] for r in v)),3),
      } for f,v in sorted(by.items())},
      "guardrail":"Development interaction test. Freeze the composition rule before new OOD families/seed if exact preservation remains 100% and savings are positive.",
      "claim_boundary":"Synthetic finite-decision economics. Cost savings compare exact optima under full exposure versus a legal typed-certificate cost model; no LLM answer-quality or real latency claim."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
