#!/usr/bin/env python3
"""Development sensitivity analysis for Evidence Certificates with call penalties.

The first certificate benchmark reduced exposure/total context cost but increased
tool calls ~20%. This experiment puts an explicit per-call penalty into BOTH the
coupled baseline and certificate policy objective, then re-optimizes each exact
policy. It asks when certificate exposure remains worthwhile once latency/RPC
cost matters.

Synthetic mechanics only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics

from discover_evidence_certificate_bench import (
    VALIDATION_COST_FRACTION_OF_ACQUISITION,
    certificate_exposure_cost,
    gen_world,
)
from run_acquisition_exposure_bench_v2 import partitions, worker_update

SEED = 71_110_927
WORLDS = 120
CERTIFICATE_FRACTIONS = (0.25, 0.50, 0.75)
CALL_PENALTIES = (0.25, 0.50, 1.0, 2.0, 4.0)
FAMILIES = ("balanced", "certificate_heavy", "semantic_heavy", "mixed_capability")


def coupled_exact(world, call_penalty):
    @functools.lru_cache(None)
    def dp(subset, used_mask):
        if world.solved(subset):
            return 0.0, 0.0, 0.0  # objective, intrinsic, calls
        best = (math.inf, math.inf, math.inf)
        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, subset, idx)
            if len(parts) <= 1:
                continue
            intrinsic = action["acquisition_cost"] + action["exposure_cost"]
            obj = intrinsic + call_penalty
            calls = 1.0
            mask = used_mask | (1 << idx)
            feasible = True
            for p, _outcome, state in parts:
                child = dp(state, mask)
                if not math.isfinite(child[0]):
                    feasible = False
                    break
                obj += p * child[0]
                intrinsic += p * child[1]
                calls += p * child[2]
            if feasible:
                cand = (obj, intrinsic, calls)
                if (cand[0], cand[2]) < (best[0], best[2]):
                    best = cand
        return best
    return dp(tuple(range(world.n)), 0)


def certificate_exact(world, certificate_fraction, call_penalty):
    n = len(world.actions)

    @functools.lru_cache(None)
    def dp(controller, worker, used_mask, hidden_mask):
        if world.solved(controller) and world.solved(worker):
            return 0.0, 0.0, 0.0, 0.0  # objective, intrinsic, calls, certificates
        best = (math.inf, math.inf, math.inf, math.inf)

        for idx in range(n):
            if not (hidden_mask & (1 << idx)):
                continue
            action = world.actions[idx]
            observed = {action["outcomes"][i] for i in controller}
            if len(observed) != 1:
                continue
            outcome = next(iter(observed))
            w2 = worker_update(world, worker, idx, outcome)
            if w2 == worker:
                continue
            child = dp(controller, w2, used_mask, hidden_mask & ~(1 << idx))
            if not math.isfinite(child[0]):
                continue
            cert = bool(action.get("certificate_capable"))
            exp = certificate_exposure_cost(action, certificate_fraction) if cert else action["exposure_cost"]
            # Exposing already-acquired evidence is local serialization, not a new
            # external tool call in this model.
            cand = (exp + child[0], exp + child[1], child[2], (1.0 if cert else 0.0) + child[3])
            if (cand[0], cand[2]) < (best[0], best[2]):
                best = cand

        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, controller, idx)
            if len(parts) <= 1:
                known = {action["outcomes"][i] for i in controller}
                if action["kind"] != "semantic" or len(known) != 1:
                    continue
                outcome = next(iter(known))
                w2 = worker_update(world, worker, idx, outcome)
                if w2 == worker:
                    continue
                child = dp(controller, w2, used_mask | (1 << idx), hidden_mask)
                intrinsic = action["acquisition_cost"] + action["exposure_cost"]
                cand = (intrinsic + call_penalty + child[0], intrinsic + child[1], 1.0 + child[2], child[3])
                if (cand[0], cand[2]) < (best[0], best[2]):
                    best = cand
                continue

            acq = action["acquisition_cost"]
            exp = action["exposure_cost"] if action["kind"] == "semantic" else 0.0
            intrinsic = acq + exp
            obj = intrinsic + call_penalty
            calls = 1.0
            certs = 0.0
            next_used = used_mask | (1 << idx)
            next_hidden = hidden_mask | (1 << idx) if action["kind"] == "structured" else hidden_mask
            feasible = True
            for p, outcome, c2 in parts:
                w2 = worker_update(world, worker, idx, outcome) if action["kind"] == "semantic" else worker
                child = dp(c2, w2, next_used, next_hidden)
                if not math.isfinite(child[0]):
                    feasible = False
                    break
                obj += p * child[0]
                intrinsic += p * child[1]
                calls += p * child[2]
                certs += p * child[3]
            if feasible:
                cand = (obj, intrinsic, calls, certs)
                if (cand[0], cand[2]) < (best[0], best[2]):
                    best = cand
        return best

    init = tuple(range(world.n))
    return dp(init, init, 0, 0)


def main():
    rng = random.Random(SEED)
    worlds = []
    for i in range(WORLDS):
        fam = FAMILIES[i % len(FAMILIES)]
        worlds.append(gen_world(rng.randrange(1_000_000_000), fam))

    grid = []
    for penalty in CALL_PENALTIES:
        baselines = [coupled_exact(w, penalty) for w in worlds]
        base_obj = statistics.fmean(x[0] for x in baselines)
        base_intrinsic = statistics.fmean(x[1] for x in baselines)
        base_calls = statistics.fmean(x[2] for x in baselines)
        for fraction in CERTIFICATE_FRACTIONS:
            certs = [certificate_exact(w, fraction, penalty) for w in worlds]
            cert_obj = statistics.fmean(x[0] for x in certs)
            cert_intrinsic = statistics.fmean(x[1] for x in certs)
            cert_calls = statistics.fmean(x[2] for x in certs)
            cert_count = statistics.fmean(x[3] for x in certs)
            grid.append({
                "call_penalty": penalty,
                "certificate_fraction": fraction,
                "effective_cost_reduction_pct": round(100 * (1 - cert_obj / base_obj), 3),
                "intrinsic_context_cost_reduction_pct": round(100 * (1 - cert_intrinsic / base_intrinsic), 3),
                "tool_call_change_pct": round(100 * (cert_calls / base_calls - 1), 3),
                "mean_certificates": round(cert_count, 4),
                "baseline_effective_cost": round(base_obj, 6),
                "certificate_effective_cost": round(cert_obj, 6),
            })

    break_even = {}
    for fraction in CERTIFICATE_FRACTIONS:
        positive = [r for r in grid if r["certificate_fraction"] == fraction and r["effective_cost_reduction_pct"] > 0]
        break_even[str(fraction)] = max((r["call_penalty"] for r in positive), default=None)

    result = {
        "experiment": "evidence-certificate-call-penalty-development-v0.1",
        "status": "development_only",
        "worlds": len(worlds),
        "certificate_fractions": list(CERTIFICATE_FRACTIONS),
        "call_penalties": list(CALL_PENALTIES),
        "validation_cost_fraction_of_acquisition": VALIDATION_COST_FRACTION_OF_ACQUISITION,
        "grid": grid,
        "largest_tested_call_penalty_with_positive_savings_by_certificate_fraction": break_even,
        "quality_invariant": "Both conditions are exact DPs under the same decision-sufficiency requirement. Certificate exposure is legal only for typed certificate-capable structured evidence and preserves exact observed outcome + provenance; semantic evidence remains full exposure.",
        "claim_boundary": "Synthetic cost units. Call penalty is a sensitivity parameter, not measured network latency. Real adoption requires measuring backend call overhead, serialization/token cost, and validation cost on Web GPT/Codex or another runtime.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
