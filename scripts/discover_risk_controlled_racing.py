#!/usr/bin/env python3
"""Development calibration for risk-controlled sequential racing.

Unlike prior heuristic searches, policy eligibility is controlled by an exact
one-sided binomial upper confidence bound on a predeclared catastrophic-loss
event. Multiple candidate policies are protected with Bonferroni correction.

Catastrophic loss event:
    adaptive environment cost > 1.10 * fixed-K8 environment cost

Target:
    P(catastrophic loss) <= 1% with family-wise confidence >= 95%

If no candidate can be certified, the output selects fixed K=8.
Development/calibration only. Freeze a certified policy before any IID/OOD test.
"""
from __future__ import annotations

import json, math, random, statistics
from dataclasses import asdict

from discover_sequential_rollout_racing import RacingPolicy, evaluate
from run_context_action_dominance_bench import gen_world

CAL_SEED = 733_291_407
CAL_WORLDS = 900
TARGET_RISK = 0.01
FAMILYWISE_DELTA = 0.05
CATASTROPHIC_DELTA = 0.10
MEAN_DEGRADATION_GATE = 0.005


def candidate_policies():
    for rounds in (4,5,6,7):
        for z in (0.5,0.75,1.0,1.5):
            for gap in (0.0,0.02,0.05):
                yield RacingPolicy(rounds,z,gap)


def binom_cdf(k: int, n: int, p: float) -> float:
    # Stable enough for n<=1000 and small k by recurrence from P(X=0).
    if p <= 0: return 1.0
    if p >= 1: return 1.0 if k >= n else 0.0
    q = 1.0-p
    term = q**n
    total = term
    for i in range(k):
        term *= (n-i)/(i+1) * p/q
        total += term
    return min(1.0,max(0.0,total))


def clopper_pearson_upper(k: int, n: int, delta: float) -> float:
    if k >= n: return 1.0
    # Solve P_{Bin(n,p)}(X <= k) = delta for upper endpoint.
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid=(lo+hi)/2
        if binom_cdf(k,n,mid) > delta:
            lo=mid
        else:
            hi=mid
    return hi


def main():
    policies=list(candidate_policies())
    per_policy_delta=FAMILYWISE_DELTA/len(policies)
    rng=random.Random(CAL_SEED)
    fams=("mixed","light_redundancy","heavy_redundancy","costly_coarse")
    worlds=[gen_world(rng.randrange(1_000_000_000),fams[i%len(fams)]) for i in range(CAL_WORLDS)]

    baseline=[]
    valid=[]
    for i,w in enumerate(worlds):
        seed=CAL_SEED+i*73
        be,bc=evaluate(w,seed,None)
        if math.isfinite(be) and math.isfinite(bc):
            valid.append((i,w,seed,be,bc)); baseline.append((be,bc))
    base_e=statistics.fmean(x[0] for x in baseline)
    base_c=statistics.fmean(x[1] for x in baseline)

    rows=[]
    for policy in policies:
        envs=[]; comps=[]; deltas=[]
        for _i,w,seed,be,_bc in valid:
            ae,ac=evaluate(w,seed,policy)
            envs.append(ae); comps.append(ac); deltas.append(ae/be-1.0)
        failures=sum(d>CATASTROPHIC_DELTA+1e-12 for d in deltas)
        upper=clopper_pearson_upper(failures,len(deltas),per_policy_delta)
        mean_delta=statistics.fmean(envs)/base_e-1
        comp_red=1-statistics.fmean(comps)/base_c
        certified=(upper<=TARGET_RISK+1e-12 and mean_delta<=MEAN_DEGRADATION_GATE+1e-12)
        rows.append({
          "policy":policy,
          "failures":failures,
          "empirical_catastrophic_rate":failures/len(deltas),
          "cp_upper":upper,
          "mean_delta":mean_delta,
          "compute_reduction":comp_red,
          "max_delta":max(deltas),
        })

    eligible=[r for r in rows if r["cp_upper"]<=TARGET_RISK+1e-12 and r["mean_delta"]<=MEAN_DEGRADATION_GATE+1e-12 and r["compute_reduction"]>0]
    eligible.sort(key=lambda r:(r["compute_reduction"],-r["cp_upper"],-r["mean_delta"]),reverse=True)
    winner=eligible[0] if eligible else None

    def out(r):
        return {
          "policy":asdict(r["policy"]),
          "calibration_catastrophic_failures":r["failures"],
          "empirical_catastrophic_rate_pct":round(100*r["empirical_catastrophic_rate"],4),
          "familywise_cp_upper_risk_pct":round(100*r["cp_upper"],4),
          "mean_environment_change_pct":round(100*r["mean_delta"],4),
          "max_environment_change_pct":round(100*r["max_delta"],4),
          "rollout_sample_reduction_pct":round(100*r["compute_reduction"],4),
        }

    result={
      "experiment":"risk-controlled-racing-calibration-v0.1",
      "status":"development_calibration_only",
      "calibration_worlds":len(valid),
      "candidate_policies":len(policies),
      "target_catastrophic_risk_pct":100*TARGET_RISK,
      "catastrophic_event_threshold_pct":100*CATASTROPHIC_DELTA,
      "familywise_confidence_pct":100*(1-FAMILYWISE_DELTA),
      "per_policy_delta":per_policy_delta,
      "mean_degradation_gate_pct":100*MEAN_DEGRADATION_GATE,
      "fixed_k8":{"mean_environment_cost":round(base_e,6),"mean_rollout_samples":round(base_c,3)},
      "certified_candidate_count":len(eligible),
      "selected":out(winner) if winner else None,
      "top_certified":[out(r) for r in eligible[:10]],
      "best_uncertified_by_compute":[out(r) for r in sorted([x for x in rows if x not in eligible],key=lambda r:r["compute_reduction"],reverse=True)[:5]],
      "decision":"freeze_selected_policy" if winner else "retain_fixed_k8",
      "guardrail":"Candidate family and risk event were fixed before this calibration run. Bonferroni correction controls selection across the candidate family. A selected policy must be frozen before new IID/OOD test seeds are introduced.",
      "claim_boundary":"Exact binomial calibration controls only the defined catastrophic event under calibration/test exchangeability. It does not guarantee distribution-shift safety, mean answer quality, or real LLM latency."
    }
    print(json.dumps(result,indent=2))

if __name__=="__main__": main()
