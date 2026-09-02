#!/usr/bin/env python3
"""Sealed OOD economics test for frozen Typed Evidence Certificate v0.1."""
from __future__ import annotations

import json, math, random, statistics
from collections import defaultdict

from run_acquisition_exposure_bench_v2 import World
from discover_certificate_call_penalty import coupled_exact, certificate_exact

FREEZE_COMMIT = "1389694f48fa26240b8386045cff6d4e6b7beebc"
SEALED_SEED = 802_631_449
CERT_FRACTION = 0.75
CALL_PENALTIES = (0.5, 1.0, 2.0, 4.0)
WORLDS_PER_FAMILY = 45
FAMILIES = (
    "typed_sparse",
    "typed_expensive_payload",
    "mixed_semantic_fallback",
    "typed_multi_stage",
    "mostly_semantic_negative",
    "high_validation_pressure",
)


def normalize(xs):
    z=sum(xs); return tuple(x/z for x in xs)


def part(rng,n,k):
    out=[rng.randrange(k) for _ in range(n)]
    if len(set(out))<2: out[0],out[-1]=0,1
    return tuple(out)


def make_world(seed,family):
    rng=random.Random(seed)
    n=rng.randint(5,8); dcount=rng.choice([2,2,3])
    decisions=[rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount): decisions[d%n]=d
    priors=normalize([rng.gammavariate(rng.uniform(.5,2.0),1.0) for _ in range(n)])
    actions=[]

    if family=="typed_sparse": structured_p=.45; cert_p=.65
    elif family=="typed_expensive_payload": structured_p=.8; cert_p=.9
    elif family=="mixed_semantic_fallback": structured_p=.55; cert_p=.55
    elif family=="typed_multi_stage": structured_p=.85; cert_p=.8
    elif family=="mostly_semantic_negative": structured_p=.15; cert_p=.4
    else: structured_p=.75; cert_p=.8

    for i in range(rng.randint(7,11)):
        structured=rng.random()<structured_p
        acq=math.exp(rng.uniform(math.log(.3),math.log(3.8)))
        if family=="high_validation_pressure" and structured:
            acq*=rng.uniform(2.0,4.5)
        exp=math.exp(rng.uniform(math.log(1.8),math.log(12.0)))
        if family=="typed_expensive_payload" and structured:
            exp*=rng.uniform(1.8,3.5)
        actions.append({
            "kind":"structured" if structured else "semantic",
            "outcomes":part(rng,n,rng.choice([2,3,4])),
            "acquisition_cost":acq,
            "exposure_cost":exp,
            "certificate_capable": bool(structured and rng.random()<cert_p),
            "source_id":f"sealed-{family}-{i}",
        })

    if family in {"typed_expensive_payload","typed_multi_stage","high_validation_pressure"}:
        # Typed decision-aligned evidence, intentionally not always full decision proof.
        actions.append({
            "kind":"structured",
            "outcomes":tuple(d % 2 for d in decisions),
            "acquisition_cost":rng.uniform(.4,1.4) * (2.5 if family=="high_validation_pressure" else 1.0),
            "exposure_cost":rng.uniform(7.0,18.0),
            "certificate_capable":True,
            "source_id":f"sealed-typed-index-{family}",
        })

    # Always provide a full semantic fallback; it can never be certificate-compressed.
    actions.append({
        "kind":"semantic",
        "outcomes":tuple(decisions),
        "acquisition_cost":rng.uniform(1.0,4.0),
        "exposure_cost":rng.uniform(2.0,8.5),
        "certificate_capable":False,
        "source_id":"sealed-semantic-proof",
    })
    return World(priors,tuple(decisions),actions,family)


def main():
    rng=random.Random(SEALED_SEED)
    worlds=[]
    for fam in FAMILIES:
        for _ in range(WORLDS_PER_FAMILY): worlds.append((fam,make_world(rng.randrange(1_000_000_000),fam)))

    grid=[]; all_solvable=True; semantic_cert_violation=False
    for penalty in CALL_PENALTIES:
        vals=[]; by=defaultdict(list)
        for fam,w in worlds:
            b=coupled_exact(w,penalty)
            c=certificate_exact(w,CERT_FRACTION,penalty)
            if not all(math.isfinite(x) for x in (*b,*c)):
                all_solvable=False; continue
            vals.append((b,c)); by[fam].append((b,c))
            # Contract check on generator schema: semantic actions must never advertise capability.
            if any(a["kind"]=="semantic" and a.get("certificate_capable") for a in w.actions): semantic_cert_violation=True
        bo=statistics.fmean(x[0][0] for x in vals); co=statistics.fmean(x[1][0] for x in vals)
        bi=statistics.fmean(x[0][1] for x in vals); ci=statistics.fmean(x[1][1] for x in vals)
        bc=statistics.fmean(x[0][2] for x in vals); cc=statistics.fmean(x[1][2] for x in vals)
        certs=statistics.fmean(x[1][3] for x in vals)
        grid.append({
          "call_penalty":penalty,
          "worlds":len(vals),
          "effective_cost_reduction_pct":round(100*(1-co/bo),3),
          "intrinsic_context_cost_reduction_pct":round(100*(1-ci/bi),3),
          "tool_call_change_pct":round(100*(cc/bc-1),3),
          "mean_certificates":round(certs,4),
          "by_family":{fam:{
             "effective_cost_reduction_pct":round(100*(1-statistics.fmean(x[1][0] for x in rows)/statistics.fmean(x[0][0] for x in rows)),3),
             "tool_call_change_pct":round(100*(statistics.fmean(x[1][2] for x in rows)/statistics.fmean(x[0][2] for x in rows)-1),3),
          } for fam,rows in sorted(by.items())}
        })

    gates={
      "positive_effective_savings_all_penalties":all(r["effective_cost_reduction_pct"]>0 for r in grid),
      "positive_intrinsic_context_savings_all_penalties":all(r["intrinsic_context_cost_reduction_pct"]>0 for r in grid),
      "no_semantic_certificate_capability":not semantic_cert_violation,
      "all_worlds_solvable_both_policies":all_solvable and all(r["worlds"]==len(worlds) for r in grid),
    }
    result={
      "experiment":"typed-evidence-certificate-sealed-ood-v0.1",
      "status":"sealed_after_freeze",
      "freeze_commit":FREEZE_COMMIT,
      "sealed_seed":SEALED_SEED,
      "certificate_fraction":CERT_FRACTION,
      "validation_cost_fraction_of_acquisition":0.15,
      "families":list(FAMILIES),
      "worlds":len(worlds),
      "grid":grid,
      "sealed_gate":gates,
      "passed_predeclared_all_gate":all(gates.values()),
      "quality_invariant":"Certificate-capable actions are structured only; certificate_exact preserves the exact observed typed outcome in worker state and semantic evidence remains full exposure.",
      "claim_boundary":"Post-freeze synthetic typed-tool economics only. Real runtimes require schema enforcement, provenance validation, and measured token/RPC/latency cost."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
