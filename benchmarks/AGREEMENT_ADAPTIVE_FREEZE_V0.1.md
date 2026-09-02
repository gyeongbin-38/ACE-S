# Action-Agreement Adaptive Compute Freeze v0.1

Status: **frozen before sealed OOD evaluation**

Algorithm freeze ref: `778869fec07a52d4c6af873030defba4a60cc186`

Development implementation: `scripts/discover_agreement_adaptive_rollout.py`

Frozen policy:

```text
pilot_rounds          = 2
min_agreement         = 0.75
require_feature_margin = 1.0
max_rollout_budget    = 8
```

With two pilot rounds, `min_agreement=0.75` is operationally unanimity: both independent pilot races must select the same context action before early commitment. If they disagree, the controller reuses those samples and expands each surviving candidate to the full `K=8` budget.

Development result at freeze:

- fixed K=8 mean environment cost: `1.928546`
- fixed K=8 mean rollout samples: `68.687`
- frozen policy environment-cost change: `+0.557%`
- frozen policy rollout-compute reduction: `47.495%`

## Freeze rule

No pilot count, agreement threshold, feature-margin condition, stochastic model, structural-pruning rule, rollout estimator, or action-selection/tie-break rule may change after this freeze and before the first sealed OOD result is recorded.

The sealed evaluator must introduce new random seeds and new synthetic world families that were not used by the prior margin-policy sealed suite. The prior sealed families are now seen and may only be used later as regression data, never as an unseen holdout for this policy.

## Claim boundary

This is a synthetic controller-mechanics policy. A sealed pass would support only the claim that action-agreement can reduce controller rollout samples while approximately preserving fixed-K environment economics on post-freeze synthetic distributions. It does not establish end-to-end LLM answer-quality equivalence or real API/tool-call savings.
