# Context Action Dominance — Results v0.1

Status: experimental controller-mechanics evidence. Not end-to-end LLM quality evidence.

## Frozen rule

The pruning rule was frozen at commit `c0493bfad47c17e4ae795e60373d978ee304e4e7` before the sealed/OOD generator and seed were introduced.

Action B may prune action A only when both conditions are structurally known on the current epistemic state:

1. B's observation partition refines A's observation partition; and
2. B has no higher measured immediate cost.

No semantic-similarity prediction or LLM value estimate is accepted as proof of dominance. Dominance is recomputed after observations narrow the state.

## Development result

240 synthetic finite-decision worlds:

| Metric | Result |
|---|---:|
| Exact optimum preserved | 100.0% |
| Initial candidate reduction | 44.44% |
| Rollout samples, no pruning | 151.134 |
| Rollout samples, pruned | 69.673 |
| Rollout compute reduction | 53.9% |
| Mean environment-cost change | -0.965% |

The slight environment-cost improvement is not guaranteed by the dominance theorem. In this noisy rollout implementation, removing dominated candidates also reduced opportunities for estimator/model noise to select a bad action.

## Sealed / OOD result

After freeze, a new seed (`9471137`) and four new generator families were introduced: `sparse_redundancy`, `cached_refinement`, `cross_source_overlap`, and `wide_cost`.

320 worlds were evaluated.

| Metric | No pruning | Structural dominance pruning |
|---|---:|---:|
| Mean cost / exact optimum | 1.133797× | **1.113024×** |
| Median cost / exact optimum | 1.004304× | **1.000000×** |
| P90 cost / exact optimum | 1.438796× | **1.409694×** |
| Mean rollout samples | 207.692 | **78.769** |

Additional invariants:

| Metric | Result |
|---|---:|
| Dynamic exact optimum preserved | **100.0%** |
| Initial candidate reduction | **50.626%** |
| Rollout compute reduction | **62.074%** |
| Mean environment-cost change | **-1.832%** |

### By OOD family

| Family | Candidate reduction | Mean pruned cost / optimum | Mean rollout samples |
|---|---:|---:|---:|
| sparse_redundancy | 30.628% | 1.124825× | 79.903 |
| cached_refinement | 63.726% | 1.097907× | 81.559 |
| cross_source_overlap | 63.939% | 1.108661× | 70.997 |
| wide_cost | 44.211% | 1.120701× | 82.616 |

## Interpretation

This suggests a deterministic **Context Action Frontier** should precede stochastic value estimation/rollout:

```text
candidate actions
  → hard feasibility checks
  → structural dominance pruning
  → probabilistic value estimation
  → bounded rollout
  → execute one action
```

When structural refinement and measured cost are available, the scheduler need not spend model or rollout budget comparing actions that are provably inferior.

## Claim boundary

The 100% optimal-preservation result applies to the synthetic finite-decision formulation and only to dominance relations that are structurally known. In real systems, equivalence/refinement inferred only from language or embeddings is uncertain and must not be treated as an exact pruning certificate.

These results do not establish frontier-model routing accuracy, answer-quality gains, or real-world latency/token improvements. Those require end-to-end agent traces.
