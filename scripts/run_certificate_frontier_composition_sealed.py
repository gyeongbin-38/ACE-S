#!/usr/bin/env python3
"""Sealed OOD test for frozen certificate + exact-frontier composition v0.1."""
from __future__ import annotations

import json, math, random, statistics
from collections import defaultdict

from run_certificate_frontier_composition_bench import World, exact_dp, full_cost, cert_cost, combined_keep, useful

FREEZE_COMMIT="9940fdd291e06c1a920d5c64cdea716e46317643"
SEALED_SEED=386_117_509
WORLDS_PER_FAMILY=70
FAMILIES=(
  "semantic_heavy_low_cert",
  "typed_high_payload",
  "redundant_typed_and_semantic",
  "cheap_semantic_complete",
  "expensive_typed_complete",
  "mixed_wide_cost",
)


def norm(xs): z=sum(xs); return [x/z for x in xs]
def part(rng,n,k):
    o=[rng.randrange(k) for _ in range(n)]
    if len(set(o))<2: o[0],o[-1]=0,1
    return tuple(o)


def make_world(seed,fam):
    rng=random.Random(seed); n=rng.randint(5,9); dc=rng.choice([2,2,3]); dec=[rng.randrange(dc) for _ in range(n)]
    for d in range(dc): dec[d%n]=d
    pri=norm([rng.gammavariate(rng.uniform(.35,2.1),1) for _ in range(n)])
    cfg={
      "semantic_heavy_low_cert":(.20,.45),
      "typed_high_payload":(.88,.88),
      "redundant_typed_and_semantic":(.62,.75),
      "cheap_semantic_complete":(.55,.65),
      "expensive_typed_complete":(.75,.85),
      "mixed_wide_cost":(.55,.70),
    }[fam]
    sp,cp=cfg; actions=[]
    for _ in range(rng.randint(8,13)):
        structured=rng.random()<sp
        acq=math.exp(rng.uniform(math.log(.18),math.log(5.0)))
        exposure=math.exp(rng.uniform(math.log(1.2),math.log(15.0)))
        if fam=="typed_high_payload" and structured: exposure*=rng.uniform(1.5,3.0)
        if fam=="mixed_wide_cost": acq*=rng.uniform(.4,2.5)
        actions.append({"outcomes":part(rng,n,rng.choice([2,2,3,4])),"acq":acq,"exposure":exposure,"kind":"structured" if structured else "semantic","certificate_capable":bool(structured and rng.random()<cp)})

    if fam=="cheap_semantic_complete":
        actions.append({"outcomes":tuple(dec),"acq":rng.uniform(.2,.6),"exposure":rng.uniform(1.0,2.2),"kind":"semantic","certificate_capable":False})
    elif fam=="expensive_typed_complete":
        actions.append({"outcomes":tuple(dec),"acq":rng.uniform(2.5,5.0),"exposure":rng.uniform(8.0,18.0),"kind":"structured","certificate_capable":True})
        # cheap partial semantic probes can beat the complete action
        for _ in range(3): actions.append({"outcomes":part(rng,n,2),"acq":rng.uniform(.15,.5),"exposure":rng.uniform(.8,2.0),"kind":"semantic","certificate_capable":False})
    else:
        structured=fam!="semantic_heavy_low_cert"
        actions.append({"outcomes":tuple(dec),"acq":rng.uniform(.5,2.5),"exposure":rng.uniform(2.0,10.0),"kind":"structured" if structured else "semantic","certificate_capable":bool(structured)})

    if fam=="redundant_typed_and_semantic":
        base=list(actions)
        for _ in range(10):
            src=rng.choice(base).copy(); src["acq"]*=rng.uniform(1.03,2.0); src["exposure"]*=rng.uniform(1.02,1.7); actions.append(src)
    return World(pri,dec,actions,fam)


def main():
    rng=random.Random(SEALED_SEED); rows=[]; by=defaultdict(list); semantic_violation=False
    for fam in FAMILIES:
      for _ in range(WORLDS_PER_FAMILY):
        w=make_world(rng.randrange(1_000_000_000),fam); init=tuple(range(w.n))
        semantic_violation |= any(a["kind"]=="semantic" and a.get("certificate_capable") for a in w.actions)
        b=exact_dp(w,full_cost)(init); cu=exact_dp(w,cert_cost)(init); cp=exact_dp(w,cert_cost,combined_keep)(init)
        if not all(math.isfinite(x) for x in (b,cu,cp)): continue
        u=len(useful(w,init)); k=len(combined_keep(w,init,cert_cost)[0])
        r={"family":fam,"baseline":b,"cert_unpruned":cu,"cert_pruned":cp,"reduction":1-k/u,"exact":abs(cu-cp)<=1e-9}
        rows.append(r); by[fam].append(r)
    exact=statistics.fmean(float(r["exact"]) for r in rows)
    candidate=statistics.fmean(r["reduction"] for r in rows)
    total=1-statistics.fmean(r["cert_pruned"] for r in rows)/statistics.fmean(r["baseline"] for r in rows)
    gates={"exact_optimum_preservation_100pct":abs(exact-1)<=1e-12,"positive_candidate_reduction":candidate>0,"positive_total_cost_reduction":total>0,"no_semantic_certificate":not semantic_violation,"all_worlds_solved":len(rows)==WORLDS_PER_FAMILY*len(FAMILIES)}
    result={
      "experiment":"certificate-frontier-composition-sealed-ood-v0.1",
      "status":"sealed_after_freeze",
      "freeze_commit":FREEZE_COMMIT,"sealed_seed":SEALED_SEED,"worlds":len(rows),"families":list(FAMILIES),
      "exact_optimum_preservation_pct":round(100*exact,3),
      "mean_candidate_reduction_pct":round(100*candidate,3),
      "mean_total_cost_reduction_vs_full_exposure_pct":round(100*total,3),
      "by_family":{f:{"n":len(v),"exact_pct":round(100*statistics.fmean(float(r["exact"]) for r in v),3),"candidate_reduction_pct":round(100*statistics.fmean(r["reduction"] for r in v),3),"total_cost_reduction_pct":round(100*(1-statistics.fmean(r["cert_pruned"] for r in v)/statistics.fmean(r["baseline"] for r in v)),3)} for f,v in sorted(by.items())},
      "sealed_gate":gates,"passed_predeclared_all_gate":all(gates.values()),
      "claim_boundary":"Post-freeze synthetic finite-decision OOD. No end-to-end LLM quality or measured latency claim."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
