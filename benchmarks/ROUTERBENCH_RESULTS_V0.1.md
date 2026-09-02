# ACE-S RouterBench — Three-Condition Policy Experiment v0.1.1

> Status: **controller-policy benchmark**, not a frontier-model routing benchmark.
>
> Date: 2026-09-02
>
> CI run: https://github.com/gyeongbin-38/ACE-S/actions/runs/33594790470

## Question

Does separating ACE-S routing into layers improve context-control decisions, and is layer separation alone sufficient?

Three deterministic conditions were evaluated against the same fixtures:

| Condition | Description |
|---|---|
| **A — Legacy Flat** | v0.3-style overloaded single-route precedence. One route must dominate even when the task is compositional. |
| **B — Layered Naive** | Primary domain and modifiers are separated, but activation/modifier decisions still rely on naive surface cues. |
| **C — Layered Signal-Aware** | Layered domain/modifiers plus explicit negative/near-miss boundaries and categorical signal policy. |

Two separate 20-case suites were executed:

- **Primary** — `benchmarks/routerbench-v0.1.json`
- **Stress** — `benchmarks/routerbench-stress-v0.1.json`

The stress set is separate from the primary fixture set, but it is **not a blinded holdout**: both the policy prototype and the stress cases were authored in the same experiment cycle. A future stable claim requires independently authored/unseen prompts and repeated model runs.

The existing 22-case legacy eval suite was also replayed as an activation-regression check.

## Router Score

```text
Router Score =
  0.25 × activation macro-F1
+ 0.20 × primary-domain accuracy
+ 0.20 × modifier micro-F1
+ 0.15 × fidelity accuracy
+ 0.10 × semantic full exact match
+ 0.05 × (1 - over-trigger rate)
+ 0.05 × (1 - under-trigger rate)
```

`semantic full exact match` compares modifiers as an unordered multi-label set.

## Headline results

| Condition | Primary score | Stress score | Primary exact | Stress exact | Primary over-trigger | Stress over-trigger |
|---|---:|---:|---:|---:|---:|---:|
| **A — Legacy Flat** | 62.7 | 61.2 | 30.0% | 25.0% | 0.0% | 0.0% |
| **B — Layered Naive** | 78.2 | 84.6 | 25.0% | 55.0% | **40.0%** | **40.0%** |
| **C — Layered Signal-Aware** | **92.9** | **97.8** | **75.0%** | **90.0%** | **0.0%** | **0.0%** |

Relative to A, C improved the Router Score by **+30.2 points on Primary** and **+36.6 points on Stress**.

## Primary suite — metric breakdown

| Metric | A — Legacy Flat | B — Layered Naive | C — Signal-Aware |
|---|---:|---:|---:|
| Router Score | 62.7 | 78.2 | **92.9** |
| Activation macro-F1 | 65.5% | 89.4% | **100.0%** |
| Domain accuracy | 65.0% | 90.0% | **95.0%** |
| Modifier micro-F1 | 45.2% | 73.2% | **93.3%** |
| Fidelity accuracy | 75.0% | **85.0%** | **85.0%** |
| Full exact match | 30.0% | 25.0% | **75.0%** |
| Over-trigger rate | **0.0%** | 40.0% | **0.0%** |
| Under-trigger rate | **0.0%** | **0.0%** | **0.0%** |

### Primary exact match by condition type

| Bucket | n | A | B | C |
|---|---:|---:|---:|---:|
| Negative control | 3 | **100.0%** | 33.3% | **100.0%** |
| Positive | 10 | 10.0% | 40.0% | **80.0%** |
| Mixed route | 3 | 0.0% | 0.0% | **0.0%** |
| Near miss | 3 | 66.7% | 0.0% | **100.0%** |
| Ambiguous | 1 | 0.0% | 0.0% | **100.0%** |

The **0% exact match on Primary mixed-route cases is the main remaining weakness**. C usually identifies the correct activation and core domain but misses one modifier or chooses the wrong fidelity.

## Stress suite — metric breakdown

| Metric | A — Legacy Flat | B — Layered Naive | C — Signal-Aware |
|---|---:|---:|---:|
| Router Score | 61.2 | 84.6 | **97.8** |
| Activation macro-F1 | 65.5% | 89.4% | **100.0%** |
| Domain accuracy | 55.0% | 90.0% | **100.0%** |
| Modifier micro-F1 | 58.1% | 82.6% | **97.7%** |
| Fidelity accuracy | 65.0% | **95.0%** | **95.0%** |
| Full exact match | 25.0% | 55.0% | **90.0%** |
| Over-trigger rate | **0.0%** | 40.0% | **0.0%** |
| Under-trigger rate | **0.0%** | **0.0%** | **0.0%** |

### Stress exact match by condition type

| Bucket | n | A | B | C |
|---|---:|---:|---:|---:|
| Lexical trap | 4 | **100.0%** | 0.0% | **100.0%** |
| Negative control | 1 | 0.0% | **100.0%** | **100.0%** |
| Semantic positive | 10 | 10.0% | **80.0%** | **80.0%** |
| Mixed route | 2 | 0.0% | **100.0%** | **100.0%** |
| Near miss | 2 | 0.0% | 0.0% | **100.0%** |
| Ambiguous | 1 | 0.0% | 0.0% | **100.0%** |

## What the experiment says

### 1. Layer separation helps, but layers alone are not enough

B substantially improves domain/modifier representation compared with A, but its **40% over-trigger rate** is unacceptable. Surface terms such as `latest`, `current`, `repository`, or `research` activate context retrieval even when the task explicitly says not to retrieve.

This supports a two-part architecture:

```text
Layer separation
+
explicit classification boundaries / negative controls
```

not layer separation by itself.

### 2. Single-route routing loses compositional information

A cannot naturally preserve combinations such as:

```yaml
primary_domain: CODE
modifiers: [TEMPORAL, EVIDENCE_CRITICAL, PLAN_AWARE]
```

This is reflected in low modifier F1 and near-zero mixed-route exact match.

### 3. Signal-aware activation solves the largest over-trigger failure in this prototype

C reached 100% activation macro-F1 and 0% over/under-trigger on both 20-case suites. This is encouraging, but should not yet be treated as an LLM routing result: it is the behavior of the deterministic prototype policy against authored fixtures.

## Remaining C failures

### Primary suite

1. `research-current-repo`
   - correct: CODE + TEMPORAL + EVIDENCE_CRITICAL + PLAN_AWARE / EXTRACT
   - predicted: CODE + TEMPORAL + PLAN_AWARE / EXTRACT
   - issue: **missed EVIDENCE_CRITICAL**

2. `plan-handoff`
   - correct: CODE + PLAN_AWARE + EVIDENCE_CRITICAL / EXTRACT
   - predicted: GENERAL + TEMPORAL + EVIDENCE_CRITICAL + PLAN_AWARE / INDEX
   - issue: **handoff/domain semantics and false TEMPORAL**

3. `tool-discovery`
   - correct: GENERAL + TOOL_DISCOVERY / INDEX
   - predicted: GENERAL + TEMPORAL + TOOL_DISCOVERY / INDEX
   - issue: **`current environment` interpreted as time-sensitive**

4. `mixed-doc-current-law`
   - correct: LONG_DOCUMENT + TEMPORAL + EVIDENCE_CRITICAL / RAW
   - predicted: same dimensions / EXTRACT
   - issue: **fidelity too low**

5. `mixed-code-tool-discovery`
   - correct: CODE + TOOL_DISCOVERY / INDEX
   - predicted: CODE + TOOL_DISCOVERY / EXTRACT
   - issue: **fidelity too high**

### Stress suite

1. `stress-code-capability`
   - correct fidelity: INDEX
   - predicted fidelity: EXTRACT

2. `stress-tool-discovery`
   - false `TEMPORAL` modifier from environment-language cues.

The remaining errors cluster around two boundaries:

- **TEMPORAL means answer freshness/version sensitivity, not merely the presence of words such as `current`.**
- **TOOL_DISCOVERY should usually begin at capability/index fidelity before inspecting source content.**

## Legacy activation regression

All three conditions scored the same on the old 22-case activation-only replay:

| Condition | Activation accuracy | Over-trigger | Under-trigger |
|---|---:|---:|---:|
| A | 90.9% | 0.0% | 10.5% |
| B | 90.9% | 0.0% | 10.5% |
| C | 90.9% | 0.0% | 10.5% |

Failures: `untrusted-retrieval-boundary`, `aggregation`.

This indicates the old eval suite is **not discriminative enough for the new layered architecture**. It remains useful as a regression suite, not as the primary routing benchmark.

## Existing RepoReplay remains separate

The existing Popular Repo Replay benchmark still validates independently:

| Metric | Baseline | ACE-S |
|---|---:|---:|
| Exact target localization | 13/21 | **20/21** |
| Canonical target localization | 14/21 | **21/21** |
| Mean ACE-S retrieval rounds | — | **1.381** |
| RepoReplay Score | 72.9/100 | **90.2/100** |

RouterBench and RepoReplay measure different things and should not be combined into one headline accuracy claim.

## Next evidence gate

Before promoting the layered controller as a measured v0.4 improvement:

1. fix the TEMPORAL semantic boundary and TOOL_DISCOVERY fidelity boundary;
2. add independently authored unseen prompts;
3. run the same structured-output router prompt across multiple frontier models with repeated trials;
4. report activation/domain/modifier/fidelity metrics by model and bucket;
5. run end-to-end ACE-S OFF vs ON agent tasks to measure task success, tokens, retrieval rounds, latency, and reacquisition overhead.

Until those gates pass, the defensible claim is:

> **In the deterministic policy prototype, layered + signal-aware control substantially outperformed both the legacy flat route and naive layered routing on the current authored RouterBench suites, while exposing mixed-route fidelity and temporal-boundary failures that still need work.**
