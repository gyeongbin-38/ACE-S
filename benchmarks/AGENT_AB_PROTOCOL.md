# End-to-End Agent A/B Protocol

ACE-S does not treat retrieval replay as proof of better agent answers. Stable performance claims require a same-model, same-task **ACE-S OFF vs ON** evaluation.

## 1. Experimental question

Does enabling ACE-S improve verified task success and/or context efficiency without reducing answer quality?

Primary constraint:

```text
Quality(ACE-S ON) >= Quality(ACE-S OFF)
```

Optimization is only considered successful when that constraint holds.

## 2. Conditions

Run the same task set under two conditions:

### OFF — baseline

- same model and model version;
- same tools and permissions;
- same repository/document/source access;
- no ACE-S skill or equivalent hidden routing prompt;
- otherwise normal agent behavior.

### ON — ACE-S

- identical model and tools;
- ACE-S available from task start;
- no additional privileged information;
- no task-specific hints beyond the skill itself.

## 3. Control variables

Record and hold constant where possible:

- model identifier/version;
- context-window size;
- reasoning/temperature settings;
- tool set;
- repository commit or document version;
- network/source availability;
- task prompt;
- evaluator rubric;
- maximum task time and tool-call budget.

Randomize condition order across tasks when execution environment permits it.

## 4. Task strata

Use multiple context-problem classes rather than one aggregate benchmark.

| Stratum | Example task | What ACE-S should change |
|---|---|---|
| Direct | simple self-contained question | avoid unnecessary retrieval |
| Repository-local | bug localization / small edit | structural local expansion |
| Repository-ripple | change-impact analysis | dependency/test expansion |
| Long document | exact policy/contract lookup | index → contiguous evidence → raw |
| Research | current multi-source comparison | claim-centered source routing |
| Temporal | resolve changed/conflicting state | current-state selection + history |
| Plan-aware | research → choose → implement | retain future-utility state |
| Evidence-critical | exact API/benchmark/policy claim | raw verification + provenance |

Report results per stratum before reporting an aggregate.

## 5. Primary metrics

### Verified task success

Binary or rubric-based task correctness, judged from task-specific ground truth or an evaluator that is blind to condition.

### Trigger precision

Among tasks where additional context is unnecessary, how often does ACE-S correctly remain dormant?

```text
trigger_precision = correct_non_activation / all_cases_where_activation_not_needed
```

### Context efficiency

Record raw metrics separately:

- model input tokens;
- model output tokens;
- worker-visible evidence tokens/bytes;
- controller-only evidence tokens/bytes;
- tool/RPC call count;
- retrieval rounds;
- files/pages/sources opened;
- cache hits and misses where observable;
- unique expensive value/model evaluations where observable;
- algorithmic sample draws when a sampling controller is used;
- wall-clock latency;
- model-compute latency if separately observable;
- tool/network latency if separately observable.

Do not equate rollout/sample draws with expensive model calls. A memoized controller can draw many samples while evaluating only a small number of unique successor states.

Do not collapse these metrics into one score until the raw metrics and cost assumptions are reported.

### Evidence and certificate accounting

For every answer-changing evidence item, record:

```text
source_ref
source_type
fidelity
raw_bytes_or_tokens
worker_exposed_bytes_or_tokens
controller_only_bytes_or_tokens
certificate_used
certificate_schema
certificate_bytes_or_tokens
validator_or_adapter
provenance_ref
```

If an Evidence Certificate is used, the trace must show that:

- the source action was explicitly typed and certificate-capable;
- the exact observed typed outcome was preserved;
- provenance/raw recovery remained available;
- semantic/free-text evidence was not certificate-compressed;
- worker-visible state after the certificate was sufficient for the final claim/action.

A certificate without these trace fields does not count as a validated certificate optimization.

## 6. Tail-risk metrics

Average efficiency and average quality are insufficient for a Quality-First controller.

For paired OFF/ON task deltas, report at least:

- mean;
- median;
- P90;
- P95;
- worst observed regression;
- fraction of tasks worse by >1%;
- fraction of tasks worse by >10% when a continuous cost/quality metric permits it;
- CVaR or mean of the worst 5% for sufficiently large task sets.

A large rare regression must not be hidden by favorable mean/P90 numbers.

For any adaptive-compute / early-stop mechanism, predeclare the tolerated risk event and risk budget before the held-out evaluation. If statistical calibration is used, report the calibration set, candidate-selection correction, assumptions, and whether the held-out data is IID or distribution-shifted.

## 7. Failure taxonomy

Every failed or degraded run should be assigned at least one cause:

```text
MISS_CONTEXT       required evidence never retrieved
OVER_CONTEXT       irrelevant context displaced or distracted
WRONG_ROUTE        context problem was misclassified
WRONG_RESOLUTION   summary used when exact evidence was needed, or raw loaded too early
STALE_STATE        superseded information controlled the answer
PROVENANCE_BREAK   claim could not be traced to source truth
CERTIFICATE_BREAK  compact typed evidence did not preserve the required worker-visible fact
BOUND_ERROR         pruning used an invalid or stale feasibility/cost bound
EARLY_STOP         sufficiency/risk gate stopped too soon
LATE_STOP          retrieval continued after evidence was sufficient
HANDOFF_LOSS       future-critical state was compacted away
OTHER              documented separately
```

Publish failure counts for both OFF and ON conditions.

## 8. Scoring policy

Do not claim ACE-S is better because it used fewer tokens alone.

Recommended decision rule:

```text
PASS when:
1. verified success is non-inferior to baseline; and
2. no predeclared quality/tail-risk gate fails; and
3. at least one efficiency metric improves materially;

OR

verified success improves materially without unacceptable efficiency regression.
```

For larger task sets, report confidence intervals or paired bootstrap estimates rather than only point estimates.

A controller mechanism that fails a predeclared worst-case/tail gate remains experimental even if its mean score improves.

## 9. Minimum release evidence

Before removing the `alpha` label from a general performance claim, publish:

- task list or reproducible task generator;
- model/version and environment;
- OFF and ON raw results;
- evaluator rubric;
- per-action trace schema above;
- failures and no-uplift cases;
- aggregate and per-stratum metrics;
- tail-risk metrics;
- exact scoring/accounting code;
- cost-model assumptions where a composite cost is reported.

## 10. Anti-gaming rules

- Do not tune ACE-S against hidden test answers.
- Do not give ON runs tools or source hints unavailable to OFF runs.
- Do not discard tasks where ACE-S regresses.
- Do not merge retrieval-policy metrics with answer-accuracy metrics.
- Do not compare token counts across different models as if they were same-condition A/B results.
- Do not report synthetic results as end-to-end agent quality.
- Do not report sample-draw reductions as model-compute reductions without cache-aware/latency evidence.
- Do not use a semantic summary as an `EvidenceCertificate` merely because it is shorter.
- Do not choose risk thresholds on the final held-out/OOD set.

## 11. Planned first matrix

The initial public matrix should target at least three agent surfaces:

```text
Codex       × OFF / ON
Claude Code × OFF / ON
OpenCode    × OFF / ON
```

Each surface should include the same high-level strata even when tool APIs differ.

The first real-runtime trace collector must store enough raw accounting to answer these questions without reconstructing them after the run:

```text
Did quality change?
What context was acquired?
What reached the worker?
What was certificate-compressed?
How many calls occurred?
What was cached/reused?
What was actual elapsed latency?
```

This protocol is intentionally conservative: ACE-S is a quality-preserving context optimization project, so efficiency gains do not count when correctness or evidence reliability drops.
