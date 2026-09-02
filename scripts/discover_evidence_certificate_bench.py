#!/usr/bin/env python3
"""Development benchmark for typed evidence certificates.

Question: after a structured tool result narrows controller uncertainty, can the
worker receive a small, source-grounded certificate of the exact observed typed
outcome instead of the full structured payload, while preserving the same
worker-visible decision state?

Certificates are permitted only for explicitly certificate-capable structured
actions. Semantic actions always require normal exposure. Every certificate is
modeled as carrying the exact typed outcome plus a provenance reference and pays
both serialization and validation cost. We sweep certificate cost fractions
rather than assuming compression is free.

Synthetic controller mechanics only.
"""
from __future__ import annotations

import functools
import json
import math
import random
import statistics
from collections import defaultdict

from run_acquisition_exposure_bench_v2 import (
    World,
    coupled_exact,
    partitions,
    worker_update,
)

SEED = 41_503_901
WORLDS = 260
CERTIFICATE_FRACTIONS = (0.10, 0.25, 0.50, 0.75, 1.00)
VALIDATION_COST_FRACTION_OF_ACQUISITION = 0.15


def random_partition(rng, n, k):
    out = [rng.randrange(k) for _ in range(n)]
    if len(set(out)) < 2:
        out[0], out[-1] = 0, 1
    return tuple(out)


def gen_world(seed, family):
    rng = random.Random(seed)
    n = rng.randint(5, 7)
    dcount = rng.choice([2, 2, 3])
    decisions = [rng.randrange(dcount) for _ in range(n)]
    for d in range(dcount):
        decisions[d % n] = d
    raw = [rng.gammavariate(rng.uniform(0.4, 2.0), 1.0) for _ in range(n)]
    z = sum(raw)
    priors = [x / z for x in raw]

    structured_p = {
        "balanced": 0.55,
        "certificate_heavy": 0.82,
        "semantic_heavy": 0.20,
        "mixed_capability": 0.65,
    }[family]
    cert_p = {
        "balanced": 0.65,
        "certificate_heavy": 0.92,
        "semantic_heavy": 0.45,
        "mixed_capability": 0.50,
    }[family]

    actions = []
    for idx in range(rng.randint(7, 9)):
        kind = "structured" if rng.random() < structured_p else "semantic"
        acq = math.exp(rng.uniform(math.log(0.3), math.log(3.2)))
        exp = math.exp(rng.uniform(math.log(2.0), math.log(14.0)))
        if kind == "structured":
            exp *= rng.uniform(1.0, 1.6)
        actions.append({
            "kind": kind,
            "outcomes": random_partition(rng, n, rng.choice([2, 3, 4])),
            "acquisition_cost": acq,
            "exposure_cost": exp,
            "certificate_capable": kind == "structured" and rng.random() < cert_p,
            "source_id": f"src-{family}-{idx}",
        })

    if family in {"certificate_heavy", "mixed_capability"}:
        # Explicit typed index aligned to a coarse decision property. It is cheap
        # to acquire but expensive to expose in full, making certificate economics
        # measurable without granting any semantic shortcut.
        actions.append({
            "kind": "structured",
            "outcomes": tuple(d % 2 for d in decisions),
            "acquisition_cost": rng.uniform(0.2, 0.7),
            "exposure_cost": rng.uniform(6.0, 13.0),
            "certificate_capable": True,
            "source_id": f"typed-index-{family}",
        })

    # Worker-sufficient semantic proof fallback.
    actions.append({
        "kind": "semantic",
        "outcomes": tuple(decisions),
        "acquisition_cost": rng.uniform(1.3, 3.8),
        "exposure_cost": rng.uniform(2.5, 8.0),
        "certificate_capable": False,
        "source_id": "semantic-proof",
    })
    return World(priors, decisions, actions, family)


def certificate_exposure_cost(action, fraction):
    # The typed witness includes source/provenance + exact observed enum/value.
    # Serialization scales with payload fraction; validation is charged separately.
    validation = VALIDATION_COST_FRACTION_OF_ACQUISITION * action["acquisition_cost"]
    serialization = fraction * action["exposure_cost"]
    return validation + serialization


def decoupled_certificate_exact(world, certificate_fraction):
    n = len(world.actions)

    @functools.lru_cache(None)
    def dp(controller, worker, used_mask, hidden_mask):
        if world.solved(controller) and world.solved(worker):
            return 0.0, 0.0, 0.0, 0.0, 0.0  # total, acq, exposure, calls, certs
        best = (math.inf, math.inf, math.inf, math.inf, math.inf)

        # Expose a hidden structured result. Certificate-capable actions may use a
        # compact exact typed witness; non-capable actions pay full exposure.
        for idx in range(n):
            if not (hidden_mask & (1 << idx)):
                continue
            action = world.actions[idx]
            outcomes = {action["outcomes"][i] for i in controller}
            if len(outcomes) != 1:
                continue
            observed = next(iter(outcomes))
            w2 = worker_update(world, worker, idx, observed)
            if w2 == worker:
                continue
            child = dp(controller, w2, used_mask, hidden_mask & ~(1 << idx))
            if not math.isfinite(child[0]):
                continue
            cert = bool(action.get("certificate_capable"))
            exp = certificate_exposure_cost(action, certificate_fraction) if cert else action["exposure_cost"]
            cand = (exp + child[0], child[1], exp + child[2], child[3], (1.0 if cert else 0.0) + child[4])
            if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                best = cand

        # Acquire new evidence. Structured result initially stays controller-only;
        # semantic result is exposed immediately and narrows both states.
        for idx, action in enumerate(world.actions):
            if used_mask & (1 << idx):
                continue
            parts = partitions(world, controller, idx)
            if len(parts) <= 1:
                known = {action["outcomes"][i] for i in controller}
                if action["kind"] != "semantic" or len(known) != 1:
                    continue
                observed = next(iter(known))
                w2 = worker_update(world, worker, idx, observed)
                if w2 == worker:
                    continue
                child = dp(controller, w2, used_mask | (1 << idx), hidden_mask)
                acq, exp = action["acquisition_cost"], action["exposure_cost"]
                cand = (acq + exp + child[0], acq + child[1], exp + child[2], 1.0 + child[3], child[4])
                if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                    best = cand
                continue

            acq = action["acquisition_cost"]
            exp = action["exposure_cost"] if action["kind"] == "semantic" else 0.0
            total, acq_sum, exp_sum, calls, certs = acq + exp, acq, exp, 1.0, 0.0
            next_used = used_mask | (1 << idx)
            next_hidden = hidden_mask | (1 << idx) if action["kind"] == "structured" else hidden_mask
            feasible = True
            for p, outcome, c2 in parts:
                w2 = worker_update(world, worker, idx, outcome) if action["kind"] == "semantic" else worker
                child = dp(c2, w2, next_used, next_hidden)
                if not math.isfinite(child[0]):
                    feasible = False
                    break
                total += p * child[0]
                acq_sum += p * child[1]
                exp_sum += p * child[2]
                calls += p * child[3]
                certs += p * child[4]
            if feasible:
                cand = (total, acq_sum, exp_sum, calls, certs)
                if (cand[0], cand[2], cand[3]) < (best[0], best[2], best[3]):
                    best = cand

        return best

    initial = tuple(range(world.n))
    return dp(initial, initial, 0, 0)


def summarize(values):
    xs = sorted(values)
    return {
        "mean": round(statistics.fmean(xs), 6),
        "median": round(statistics.median(xs), 6),
        "p90": round(xs[int(0.90 * (len(xs)-1))], 6),
    }


def main():
    rng = random.Random(SEED)
    families = ("balanced", "certificate_heavy", "semantic_heavy", "mixed_capability")
    worlds = []
    for i in range(WORLDS):
        fam = families[i % len(families)]
        worlds.append((fam, gen_world(rng.randrange(1_000_000_000), fam)))

    coupled = []
    valid_worlds = []
    for fam, world in worlds:
        base = coupled_exact(world)
        if all(math.isfinite(x) for x in base):
            coupled.append(base)
            valid_worlds.append((fam, world, base))

    rows = []
    for fraction in CERTIFICATE_FRACTIONS:
        vals = []
        by = defaultdict(list)
        for fam, world, base in valid_worlds:
            cert = decoupled_certificate_exact(world, fraction)
            if not all(math.isfinite(x) for x in cert):
                continue
            vals.append((base, cert))
            by[fam].append((base, cert))
        coupled_total = statistics.fmean(x[0][0] for x in vals)
        cert_total = statistics.fmean(x[1][0] for x in vals)
        coupled_exp = statistics.fmean(x[0][2] for x in vals)
        cert_exp = statistics.fmean(x[1][2] for x in vals)
        coupled_calls = statistics.fmean(x[0][3] for x in vals)
        cert_calls = statistics.fmean(x[1][3] for x in vals)
        cert_count = statistics.fmean(x[1][4] for x in vals)
        rows.append({
            "certificate_fraction": fraction,
            "worlds": len(vals),
            "total_cost_reduction_pct": round(100 * (1 - cert_total / coupled_total), 3),
            "worker_exposure_reduction_pct": round(100 * (1 - cert_exp / coupled_exp), 3),
            "tool_call_change_pct": round(100 * (cert_calls / coupled_calls - 1), 3),
            "mean_certificates": round(cert_count, 4),
            "certificate_total_cost": round(cert_total, 6),
            "by_family": {
                fam: {
                    "total_cost_reduction_pct": round(100 * (1 - statistics.fmean(v[1][0] for v in famvals) / statistics.fmean(v[0][0] for v in famvals)), 3),
                    "exposure_reduction_pct": round(100 * (1 - statistics.fmean(v[1][2] for v in famvals) / statistics.fmean(v[0][2] for v in famvals)), 3),
                }
                for fam, famvals in by.items()
            },
        })

    positive = [r for r in rows if r["total_cost_reduction_pct"] > 0]
    break_even = max((r["certificate_fraction"] for r in positive), default=None)
    result = {
        "experiment": "typed-evidence-certificate-development-v0.1",
        "status": "development_only",
        "worlds": len(valid_worlds),
        "validation_cost_fraction_of_acquisition": VALIDATION_COST_FRACTION_OF_ACQUISITION,
        "coupled_baseline": {
            "total_cost": summarize([x[0] for x in coupled]),
            "worker_exposure": summarize([x[2] for x in coupled]),
            "tool_calls": summarize([x[3] for x in coupled]),
        },
        "certificate_sensitivity": rows,
        "largest_tested_certificate_fraction_with_positive_total_savings": break_even,
        "quality_invariant": "A certificate is legal only for an explicitly certificate-capable structured action and carries the exact observed typed outcome plus source/provenance reference. Worker epistemic state is updated exactly as full structured exposure would update it. Semantic evidence is never certificate-compressed. Termination still requires both controller and worker decision sufficiency.",
        "claim_boundary": "Synthetic economics. Exact certificate semantics are contractual here; a real runtime needs typed tool schemas, provenance-preserving serialization, validators, and measured certificate/validation cost before treating these savings as realizable.",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
