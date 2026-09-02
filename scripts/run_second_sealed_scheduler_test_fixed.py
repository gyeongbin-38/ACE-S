#!/usr/bin/env python3
"""Invariant-only wrapper for the frozen second sealed scheduler test.

The first execution produced no benchmark result: it failed before evaluation because one
late-bargain generator could emit a non-monotonic cumulative payload-cost vector. This
wrapper preserves the already-published seed, families, frozen policies, and rollout rule,
and only enforces the intended invariant that cumulative fidelity payload cost cannot fall
as fidelity increases.
"""
from __future__ import annotations

import run_second_sealed_scheduler_test as sealed
import discover_resolution_scheduler as res

_original_make_resolution_ood = sealed.make_resolution_ood


def invariant_checked_make_resolution_ood(rng, family):
    ood = _original_make_resolution_ood(rng, family)
    fixed_sources = []
    for src in ood.world.sources:
        costs = []
        prev = 0.0
        for raw in src.cumulative_cost:
            value = max(float(raw), prev + 0.000001)
            costs.append(round(value, 6))
            prev = value
        fixed_sources.append(res.Source(src.outcomes, tuple(costs)))
    world = res.World(
        ood.world.decisions,
        ood.world.prior,
        tuple(fixed_sources),
        ood.world.family,
    )
    return sealed.ResolutionOOD(world, ood.call_overheads, ood.family)


sealed.make_resolution_ood = invariant_checked_make_resolution_ood

if __name__ == "__main__":
    sealed.main()
