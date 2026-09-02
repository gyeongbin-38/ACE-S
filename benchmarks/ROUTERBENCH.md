# ACE-S RouterBench

> Status: **fixture-only v0.1**. This document defines the benchmark shape and initial ground truth. It does **not** report measured model performance yet.

RouterBench measures whether an agent activates ACE-S only when useful and whether it decomposes a task into the correct context-policy dimensions.

## Why this exists

The `v0.3.x` skill used a single primary route. That is easy to describe but mixes different dimensions: `CODE` is a source/domain, while `TEMPORAL`, `PLAN_AWARE`, and `EVIDENCE` are cross-cutting constraints. Mixed tasks can therefore make several routes simultaneously correct.

`v0.4.x` evaluates the decomposition separately:

```text
Task
  ↓
Activation
  ↓
Signals
  ↓
Primary domain + modifiers + fidelity
  ↓
Context action
```

This lets routing failures be localized instead of hidden inside one end-to-end score.

## Ground-truth dimensions

### Activation

- `DIRECT` — no new context retrieval is needed.
- `ACTIVE` — context selection materially affects task quality.
- `UNCERTAIN` — one bounded check is justified before activation is resolved.

### Primary domain

- `GENERAL`
- `CODE`
- `LONG_DOCUMENT`
- `RESEARCH`
- `STATE`

### Modifiers

Multi-label:

- `TEMPORAL`
- `EVIDENCE_CRITICAL`
- `PLAN_AWARE`
- `TOOL_DISCOVERY`

### Minimum fidelity

- `INDEX`
- `SUMMARY`
- `EXTRACT`
- `RAW`

## Fixture buckets

The initial fixture set intentionally contains more than obvious positive examples:

- **positive** — clear activation cases;
- **negative_control** — should not activate retrieval just because context-related words appear;
- **near_miss** — lexical cues resemble a specialist condition but semantics do not require it;
- **mixed_route** — tasks needing one primary domain plus several modifiers;
- **ambiguous** — bounded uncertainty is the correct answer rather than forced certainty.

The fixtures live in [`routerbench-v0.1.json`](routerbench-v0.1.json).

## Metrics

When model runs are added, report layer-level metrics before any composite score:

```text
Activation Precision
Activation Recall
Activation F1
False Trigger Rate
False Direct Rate

Primary Domain Accuracy
Modifier Micro Precision / Recall / F1
Modifier Exact-Match Rate
Minimum-Fidelity Accuracy
Over-Fidelity Rate
Under-Fidelity Rate
```

Also report cross-layer failure classes:

```text
OVER_TRIGGER
UNDER_TRIGGER
WRONG_DOMAIN
MISSING_MODIFIER
EXTRA_MODIFIER
OVER_FIDELITY
UNDER_FIDELITY
```

Do not hide regressions behind a single aggregate score.

## End-to-end follow-up

RouterBench only tests policy selection. Real-agent A/B remains necessary because correct routing can still produce poor execution.

Pair RouterBench with [`AGENT_AB_PROTOCOL.md`](AGENT_AB_PROTOCOL.md) and additionally measure:

- verified task success;
- tool calls and retrieval rounds;
- input/output tokens;
- latency;
- early/late stop rate;
- repeated file/source lookups;
- **reacquisition calls**: retrieval needed mainly because previously available state was dropped or compressed too aggressively.

The quality gate remains:

```text
Quality(ACE-S ON) >= Quality(ACE-S OFF)
```

Context efficiency is secondary to preserved task quality and evidence fidelity.

## Running the fixture validator

```bash
python scripts/validate_routerbench.py
```

This checks fixture structure and label validity only. It does not call a model.

## v0.2 dataset target

Before publishing model routing claims, expand to at least 100 prompts with a deliberately hard distribution:

```text
25 obvious positive
25 negative controls
20 near-miss
20 mixed-domain/modifier
10 ambiguous/adversarial
```

Use multiple models and repeated runs where stochastic routing is possible. Publish raw predictions, model/version, prompt template, evaluator code, and all failure cases.
