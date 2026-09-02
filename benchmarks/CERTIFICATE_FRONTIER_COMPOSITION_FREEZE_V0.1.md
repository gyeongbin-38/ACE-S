# Certificate + Exact Frontier Composition v0.1 — Frozen Before Sealed OOD

Status: `FROZEN_BEFORE_SEALED_TEST`

Freeze source commit: `abad2d7b412946806d4b55c69778930af2c5d9c8`
Algorithm: `scripts/run_certificate_frontier_composition_bench.py`

## Frozen rules

1. Full-exposure baseline action cost = acquisition + full worker exposure.
2. Legal certificate action cost = acquisition + `0.75 * exposure` + `0.15 * acquisition` validation cost.
3. Semantic evidence is never certificate-capable.
4. Structural dominance is recomputed using the legal certificate-aware action cost.
5. Cost-floor pruning uses only a feasible one-step complete-plan upper bound and immediate action cost as a lower bound.
6. If no complete-plan upper bound exists, cost-floor abstains.

## Development evidence at freeze

360 synthetic finite-decision worlds:

- exact optimum preservation after certificate-aware dominance + cost-floor pruning: `100%`
- mean initial candidate reduction: `45.618%`
- mean total cost reduction versus full exposure: `8.808%`
- certificate-only total cost reduction: `8.808%`

Interpretation: typed certificates changed execution/exposure economics, while exact pruning reduced the search frontier without changing the certificate-aware optimal plan cost.

## Sealed protocol

After this freeze commit, introduce new action/evidence families and a fresh seed. Do not alter certificate fractions or pruning rules.

Predeclared sealed gates:

- exact certificate-aware optimum preservation = `100%`,
- mean candidate reduction > `0%`,
- mean total cost reduction versus full exposure > `0%`,
- no semantic action is certificate-capable,
- all worlds are solvable under baseline and certificate-aware policy.

## Claim boundary

Synthetic finite-decision economics only. No end-to-end LLM quality or measured runtime-latency claim.
