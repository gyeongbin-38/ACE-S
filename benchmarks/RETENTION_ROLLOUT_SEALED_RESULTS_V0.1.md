# Retention Rollout — Sealed OOD Results v0.1

Status: synthetic lifecycle-controller evidence, not end-to-end LLM quality evidence.

## Freeze protocol

The one-step retention rollout algorithm was frozen at commit `a8277cbd83e8ef07cda7a99c93b50d720328ee00` before the sealed lifecycle generator families and seed were introduced.

Sealed seed: `9144731`.

Fresh post-freeze lifecycle families:
- alternating_reuse
- long_idle_revival
- exactness_burst
- semantic_then_exact
- decay_then_revival
- uncertain_revival

330 lifecycle items × 3 probability-noise levels × 3 noise seeds = 2,970 evaluations.

## Results

| Metric | Frozen heuristic | One-step rollout |
|---|---:|---:|
| Mean cost / exact optimum | 1.12895× | **1.05894×** |
| Median | 1.00000× | **1.00000×** |
| P90 | 1.37861× | **1.04149×** |
| P95 | 1.81164× | **1.37099×** |
| Within +5% of optimum | 78.99% | **90.64%** |
| Within +10% | 81.95% | **92.22%** |
| Within +25% | 86.60% | **94.24%** |

Rollout beat or tied the frozen heuristic in **100.0%** of evaluated cases. Mean normalized lifecycle cost improved by **6.201%** versus the frozen heuristic.

## Family means

| Family | Frozen heuristic | Rollout |
|---|---:|---:|
| alternating_reuse | 1.14842× | **1.07090×** |
| decay_then_revival | 1.09007× | **1.01374×** |
| exactness_burst | 1.20858× | **1.03926×** |
| long_idle_revival | 1.22822× | **1.17635×** |
| semantic_then_exact | 1.01516× | **1.00271×** |
| uncertain_revival | 1.08323× | **1.05071×** |

## Interpretation

A fixed retention heuristic is especially vulnerable when reuse/exactness changes over time. Replanning RAW/ABSTRACT/DROP after each lifecycle observation generalizes to several post-freeze patterns and substantially improves tail behavior.

`long_idle_revival` remains the clearest weakness: when context appears irrelevant for a long interval and then becomes valuable again, even one-step rollout can underestimate future reacquisition cost.

## Claim boundary

The evaluator has access to the synthetic item's true need and exactness probabilities for expected-cost calculations. A real agent must estimate those probabilities from traces/state. These numbers therefore support the lifecycle-control mechanics only; they do not imply equivalent token or quality gains for GPT/Codex/web-agent workloads.
