# Selective Retention Lookahead Freeze v0.2

Status: **frozen before sealed OOD evaluation**

Algorithm implementation ref: `8909dab6f8f8af4380628ebe1bc4203d71e83191`

Frozen trigger:

```text
quiet_threshold       = 0.08
min_quiet_steps       = 2
score_threshold       = 6.0
max_future_exact_rate = 0.55

if trigger fires:
    use retention lookahead depth = 3
else:
    use retention lookahead depth = 1
```

Development result at freeze (`225` lifecycle items, `1350` stochastic evaluations):

- depth-3 invocation rate: `39.111%`
- mean cost ratio to exact optimum: `1.07423x`
- mean cost reduction vs always-depth1: `8.106%`
- fraction of always-depth3 economic gain captured: `96.339%`
- always-depth1 mean: `1.16899x`
- always-depth3 mean: `1.07063x`

The v2 ambiguity gate eliminated the main v1 waste pattern: `idle_then_exact_burst` depth-3 invocation fell to `0%` while revival-heavy families retained high selective use.

## Sealed gates fixed before OOD evaluation

A post-freeze sealed suite passes only if all are true:

1. selective mean lifecycle cost is lower than always-depth1;
2. selective policy captures at least `75%` of the economic gain of always-depth3 relative to always-depth1;
3. depth-3 invocation rate is at most `40%` of lifecycle items;
4. no deliberately obvious exact-return/no-revival family is routed to depth3 more than `20%` of items.

## Freeze rule

No trigger threshold, revival score formula, future-exactness gate, depth choice, base retention policy, or rollout evaluator may change before the first sealed result is recorded. New families/seed may be introduced only after this freeze.

## Claim boundary

This is synthetic lifecycle economics. The evaluator and trigger receive generator-level future need/exactness probabilities. Real use requires calibrated estimates from runtime traces. Depth-3 invocation rate is a compute proxy, not measured wall-clock latency or model-token cost.
