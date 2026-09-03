# Deterministic Decision Frontier

Use this when an architecture has multiple interacting decision frontiers and manual comparison is becoming unreliable.

## Principle

Separate semantic work from deterministic constraint work.

- Model/human reasoning: identify ASRs, candidate choices, consequences, uncertainty, and scenario mechanisms.
- Deterministic controller/solver: reject infeasible combinations, enforce compatibility constraints, compute non-dominated candidates, and preserve why a combination was eliminated.

Do not ask a language model to numerically optimize a large combinatorial architecture space from prose alone.

## 1. Decision variable model

Represent each real decision frontier as a bounded variable.

Example:

```text
coordination = {sync_transaction, async_event}
deployment = {single_unit, split_service}
state = {single_writer, partitioned_writer}
region = {single_region, active_passive, active_active}
```

Do not create variables for reversible details that cannot change architecture quality.

## 2. Constraints

Encode facts that can be checked without taste:

```text
if immediate_serializable_cross_aggregate_consistency:
    coordination != async_event_without_compensation

if strict_process_isolation:
    deployment != single_process

if offline_required:
    dependency != cloud_only_service
```

Each constraint should reference its originating hard constraint, ASR, or accepted decision.

## 3. Compatibility rules

Some choices are individually valid but incompatible together. Record these explicitly instead of expecting the generator to remember them across a large design.

Examples:
- active-active writes require a conflict model;
- independent deployment plus shared in-process transaction is inconsistent;
- event replay requires stable event identity/versioning;
- zero-downtime schema evolution requires compatibility across mixed versions.

## 4. Objective dimensions

Do not collapse quality into one score by default. Preserve dimensions such as:
- consistency/correctness risk
- latency
- availability/recovery
- security/isolation
- modifiability
- deployability
- operability
- infrastructure cost
- implementation complexity
- migration risk
- irreversible commitments

Dimensions may be measured, ordinal, or unknown, but their provenance must be explicit.

## 5. Frontier computation

1. enumerate or search feasible combinations;
2. remove all hard-constraint violations;
3. remove dominated candidates;
4. retain the Pareto frontier;
5. attack frontier candidates with quality scenarios;
6. update dimensions only from new evidence;
7. repeat until one candidate is preferred or the remaining decision requires stakeholder utility weights.

## 6. Unknown values

Unknown is not zero.

If a dimension is material but unknown, preserve `UNKNOWN` and identify the cheapest test/measurement that would resolve it. Do not rank a candidate as superior because its cost/risk is merely unmeasured.

## 7. Selection

A deterministic solver may select a unique winner only when stakeholder utility weights or an explicit lexicographic priority are supplied.

Without those, return:
- feasible frontier;
- dominated/eliminated candidates and reasons;
- unresolved tradeoffs;
- next measurement that can change the frontier.

This avoids laundering subjective preferences into a fake mathematical optimum.
