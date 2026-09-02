# Selective Retention Lookahead v0.3 — Frozen Before Sealed OOD

Status: `FROZEN_BEFORE_SEALED_TEST`

Freeze source commit: `963b90c6f9543ca0e42ce1a29acda9c5f8b8ee2a`
Algorithm: `scripts/discover_selective_retention_lookahead_v3.py`

## Frozen trigger

```text
quiet_threshold = 0.09
revival_threshold = 0.18
min_quiet_steps = 2
min_revival_segments = 3
pressure_threshold = 6.0
min_semantic_ambiguity = 0.60
```

The trigger computes, after a qualifying quiet interval:

- revival segment count,
- future reacquisition pressure,
- future exactness ambiguity `4*p_exact*(1-p_exact)`.

Depth-3 is selected when either:

1. at least three revival segments exist and pressure is at least `0.65 * pressure_threshold`, or
2. pressure is at least `pressure_threshold` and semantic ambiguity is at least `min_semantic_ambiguity`.

No depth-3 rollout result is consulted by the trigger itself.

## Development evidence at freeze

225 synthetic lifecycle items / 1,350 evaluations:

- always depth-1 mean ratio: `1.15770`
- always depth-3 mean ratio: `1.05897`
- selective mean ratio: `1.06348`
- selective depth-3 item rate: `39.111%`
- selective mean cost reduction vs depth-1: `8.139%`
- fraction of always-depth3 gain captured: `95.432%`

Predeclared development gate passed:

- gain capture >= 75%
- depth-3 item rate <= 40%

## Sealed-test protocol

After this freeze commit, create a new seed and new lifecycle families not used by v3 development or the v2 sealed suite. Do not alter the trigger or thresholds after seeing sealed results.

Required sealed reporting:

- always-depth1 / always-depth3 / selective mean cost ratios,
- fraction of always-depth3 gain captured,
- depth3 item rate,
- per-family depth3 rate and mean cost,
- negative-control deep-use rate.

Predeclared sealed gate:

- selective beats always-depth1,
- captures >= 75% of always-depth3 gain,
- depth3 item rate <= 40%,
- negative-control depth3 rate <= 15%.

## Claim boundary

Synthetic lifecycle economics only. The trigger uses generator-level future need/exactness probabilities; a production runtime must estimate/calibrate them. Passing this benchmark would not constitute end-to-end LLM answer-quality evidence.
