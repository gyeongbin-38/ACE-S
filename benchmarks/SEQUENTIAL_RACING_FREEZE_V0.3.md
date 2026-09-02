# Sequential Rollout Racing v0.3 — Frozen Before Sealed OOD

Status: `FROZEN_BEFORE_SEALED_TEST`

Freeze source commit: `3de1956901d6684b5da1e8c7aa6d51f280f4afd6`
Algorithm: `scripts/discover_sequential_rollout_racing_v3.py`

## Frozen policy

```text
max_rollout_rounds = 8
min_rounds = 7
z = 0.75
min_absolute_gap = 0.0
```

At each state, surviving actions are sampled in synchronized rounds. After at least seven rounds, stop at the current empirical best only when its upper interval is below every competitor's lower interval. Otherwise continue to the fixed K=8 ceiling.

The interval is an empirical controller heuristic, not a formal confidence guarantee.

## Development evidence at freeze

480 synthetic worlds, 120 candidate policies:

- fixed K=8 mean environment cost: `1.838472`
- fixed K=8 mean rollout samples: `69.602`
- selected mean environment cost: `1.838252`
- selected mean rollout samples: `63.667`
- mean environment change: `-0.012%`
- rollout compute reduction: `8.527%`
- P95 per-world environment change: `0.0%`
- worlds within +1%: `100.0%`
- max per-world environment change: `0.0%`
- CVaR95 environment change: `0.0%`

The quality gates were fixed before this fresh development seed was run:

- mean degradation <= +0.5%
- P95 degradation <= +1%
- >=97% worlds within +1%
- maximum single-world degradation <= +10%
- CVaR95 <= +3%

## Sealed protocol

After this freeze commit, create new generator families and a fresh seed not used by v1/v2/v3 development or prior adaptive-compute sealed suites. Do not change the policy or thresholds after seeing sealed outcomes.

Predeclared sealed gate:

- mean environment degradation <= +0.5%
- P95 per-world degradation <= +1%
- >=97% worlds within +1%
- max per-world degradation <= +10%
- CVaR95 <= +3%
- rollout compute reduction > 0%

If any quality gate fails, fixed K=8 remains the default. Do not weaken the gate to preserve a compute-savings claim.

## Claim boundary

Synthetic controller rollout economics only. This does not establish real-agent answer-quality equivalence, formal statistical confidence, or measured wall-clock savings.
