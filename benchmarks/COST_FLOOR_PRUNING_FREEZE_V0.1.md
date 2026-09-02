# Cost-Floor Pruning Freeze v0.1

Status: **frozen before sealed OOD evaluation**

Algorithm implementation ref: `a1ecbf10a1240390c9ecca9c85a11fb043173d1c`

Frozen rule:

```text
Given:
  U = measured total cost of a genuinely feasible complete context plan
  c(a) = measured immediate cost of candidate first action a
  all future modeled costs are non-negative and comparable

If c(a) >= U:
  prune a
```

The rule is applied after exact structural-dominance pruning. It does not require the candidate action's observation partition to be comparable with the incumbent complete plan.

Development result at freeze (`360` synthetic worlds):

- exact optimal preservation: `100.0%`
- structural-dominance candidate reduction: `44.850%`
- combined structural + cost-floor reduction: `61.025%`
- incremental reduction of the structural frontier: `30.239%`

The development generator always supplied at least one one-step decision-sufficient action, so a feasible upper bound was available in all development worlds. The sealed suite must vary upper-bound availability, including worlds where no one-step complete plan exists; in those cases this rule must abstain rather than invent an upper bound.

## Freeze rule

No pruning inequality, upper-bound definition, structural-dominance rule, cost sign assumption, or fallback behavior may be changed before the first sealed result is recorded.

The sealed evaluator may introduce new world families, new action structures, missing one-step upper bounds, and a new random seed. It may not tune the frozen rule from those outcomes.

## Claim boundary

Exactness applies only when `U` is a real feasible complete-plan upper bound and all future costs are non-negative and in the same accounting units. An estimated LLM score, uncertain latency prediction, or heuristic expected cost must never be promoted to an exact pruning bound. When no valid `U` exists, the cost-floor layer abstains and leaves the frontier unchanged.
