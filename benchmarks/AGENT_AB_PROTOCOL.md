# End-to-End Agent A/B Protocol

ACE-S does not treat retrieval replay as proof of better agent answers. Stable performance claims require a same-model, same-task **ACE-S OFF vs ON** evaluation.

This document defines the release-gate protocol for that test.

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

Record:

- input tokens;
- output tokens;
- tool-call count;
- retrieval rounds;
- files/pages/sources opened;
- wall-clock latency.

Do not collapse these into one number until raw metrics are reported.

## 6. Failure taxonomy

Every failed or degraded run should be assigned at least one cause:

```text
MISS_CONTEXT       required evidence never retrieved
OVER_CONTEXT       irrelevant context displaced or distracted
WRONG_ROUTE        context problem was misclassified
WRONG_RESOLUTION   summary used when exact evidence was needed, or raw loaded too early
STALE_STATE        superseded information controlled the answer
PROVENANCE_BREAK   claim could not be traced to source truth
EARLY_STOP         sufficiency gate stopped too soon
LATE_STOP          retrieval continued after evidence was sufficient
HANDOFF_LOSS       future-critical state was compacted away
OTHER              documented separately
```

Publish failure counts for both OFF and ON conditions.

## 7. Scoring policy

Do not claim ACE-S is better because it used fewer tokens alone.

Recommended decision rule:

```text
PASS when:
1. verified success is non-inferior to baseline; and
2. at least one efficiency metric improves materially; or
3. verified success improves materially without unacceptable efficiency regression.
```

For larger task sets, report confidence intervals or paired bootstrap estimates rather than only point estimates.

## 8. Minimum release evidence

Before removing the `alpha` label from a general performance claim, publish:

- task list or reproducible task generator;
- model/version and environment;
- OFF and ON raw results;
- evaluator rubric;
- failures and no-uplift cases;
- aggregate and per-stratum metrics;
- exact scoring code.

## 9. Anti-gaming rules

- Do not tune ACE-S against hidden test answers.
- Do not give ON runs tools or source hints unavailable to OFF runs.
- Do not discard tasks where ACE-S regresses.
- Do not merge retrieval-policy metrics with answer-accuracy metrics.
- Do not compare token counts across different models as if they were same-condition A/B results.
- Do not report synthetic results as end-to-end agent quality.

## 10. Planned first matrix

The initial public matrix should target at least three agent surfaces:

```text
Codex      × OFF / ON
Claude Code × OFF / ON
OpenCode   × OFF / ON
```

Each surface should include the same high-level strata even when tool APIs differ.

This protocol is intentionally conservative: ACE-S is a quality-preserving context optimization project, so efficiency gains do not count when correctness drops.
