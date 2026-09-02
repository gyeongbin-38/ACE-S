# Adaptive Rollout Budget Freeze v0.1

Status: **frozen before sealed OOD evaluation**

Algorithm freeze ref: `6fc4a021c692f901470b239611a1921dc0f4a26e`

Development selector: `scripts/discover_adaptive_rollout_budget_v2.py`

Frozen policy:

```text
greedy_margin = 5.0
small_margin  = 1.05
small_k       = 4
medium_k      = 6
hard_k        = 8
```

Development gate:

- baseline: fixed `K=8` rollout after structural dominance pruning
- selected-policy mean environment-cost degradation must be `<= +1.0%`
- within that hard quality/cost bound, maximize rollout-compute reduction

Development result at freeze:

- mean environment cost change: `+0.791%`
- mean rollout-compute reduction: `56.427%`

## Freeze rule

No threshold, rollout budget, feature formula, stochastic model, structural-pruning rule, or action-selection rule may be changed after this freeze and before the first sealed OOD result is recorded.

The sealed evaluator may introduce new random seeds and new synthetic world families, but may not tune the frozen policy from those results.

## Claim boundary

This freezes a synthetic controller-mechanics policy, not an end-to-end LLM policy. A sealed pass only supports the claim that adaptive compute can preserve the fixed-K controller's synthetic environment economics while reducing controller rollout samples on post-freeze synthetic distributions. It does not establish real-agent answer-quality equivalence.
