# Transactional Architecture Memory Runtime v0.1

Status: `CANDIDATE_FROZEN_BEFORE_FRESH_OOD`

Base lineage: `71d7cd51dd58c188973f871aed638934bcb8ea8d`

## Research question

What architecture best preserves project/architecture constraints across long-horizon agent work while minimizing worker-visible context and preventing stale or speculative state from controlling later decisions?

## Candidate selected for fresh OOD

The v0.1 candidate is a hybrid of five mechanisms:

```text
Append-only Event Log  <---- immutable provenance / replay
        |
        v
Transactional State Tree <--- speculative branch / checkpoint / commit / rollback
        |
        v
Typed Architecture State Graph <--- canonical current state
        |
        +--> Hard-Constraint + Proof-Obligation Ledger
        |
        v
Bounded Worker Projection <--- only current decision neighborhood enters model context
```

### 1. Append-only event log

Every architecture-changing observation, decision, correction, tool-side effect, validation result, and branch transition receives a stable event id and provenance pointer. Events are never rewritten in place.

Purpose:
- exact auditability;
- source recovery;
- deterministic replay;
- distinguish current truth from historical truth.

### 2. Transactional execution-state tree

Model proposals do not mutate canonical state directly.

Each speculative subtask/branch writes to staged state:

```text
canonical checkpoint
  -> branch proposal
  -> staged mutations
  -> validate
      -> COMMIT
      -> ROLLBACK / REVISE from checkpoint
```

Only the active committed root-to-current path may control the worker. Aborted branch facts remain in the event log for audit but are excluded from canonical projections.

### 3. Typed Architecture State Graph

Canonical state uses stable ids and typed relations for:
- requirements / ASRs / hard constraints / non-goals;
- components / boundaries / state / interfaces / critical flows;
- decisions / options / risks / scenarios;
- proof obligations / fitness checks;
- evidence / provenance.

Updates are incremental: only the affected decision neighborhood is reopened.

### 4. Hard-constraint and proof-obligation ledger

Hard constraints and unresolved proof obligations are first-class pinned state, not ordinary semantic memories.

A decision cannot be committed when:
- it violates an active hard constraint;
- a required proof obligation is unresolved;
- its evidence status is stale/contradicted;
- its owner/version relation is ambiguous above the declared risk threshold.

Superseded constraints/decisions remain historical events but lose `ACTIVE` status atomically.

### 5. Bounded worker projection

The model never receives the full graph or full event log by default. A projection is generated from the current action:

```text
current goal
+ active hard constraints relevant to this goal
+ current decision neighborhood
+ unresolved proof obligations
+ exact provenance pointers
+ recent local trace
```

Expansion is one-hop / one-policy at a time. Raw history is reopened only when required for exactness, contradiction resolution, or rollback.

## Why this candidate instead of one memory structure

- Sliding/full transcript: preserves chronology but fails under context pressure.
- Semantic/vector retrieval: retrieves relevant events but can mix superseded or aborted state unless validity is separately modeled.
- Mutable graph alone: preserves relations/current state but lacks transaction semantics for speculative writes and rollback.
- Hierarchical state tree alone: preserves execution continuity/branch isolation but summary compression can weaken exact provenance and architecture-wide traceability.
- Hybrid runtime: separates history, canonical truth, speculation, obligations, and worker-visible context instead of forcing one structure to do all five jobs.

## Invariants

1. `CANONICAL != MODEL_PROPOSAL` until commit.
2. Aborted branch state never appears in a normal worker projection.
3. Every active architecture fact has a provenance pointer or explicit `ACCEPTED_INTENT` status.
4. Hard constraints and unresolved proof obligations cannot be evicted solely for recency or semantic similarity.
5. Supersession is atomic: new active version + old historical version, never two active truths silently merged.
6. Every commit emits an event and a canonical-state version.
7. Rollback changes active state, not history.
8. Worker context is a view; canonical graph/event log remain source of truth.

## Evaluation gates

Fresh OOD must report separately:
- current-state accuracy;
- hard-constraint retention;
- stale-state/supersession errors;
- aborted-branch contamination;
- proof-obligation correctness;
- provenance fidelity;
- worker-visible state cost;
- recovery after correction/rollback.

Primary quality gate:

```text
state_accuracy >= best non-hybrid baseline
AND aborted_branch_contamination == 0
AND hard_constraint_retention >= 99%
AND provenance_fidelity >= 99%
```

Efficiency is secondary and does not compensate for a failed quality gate.

## Claim boundary

This freeze selects an architecture candidate, not a production-performance claim. Synthetic controller OOD can validate state mechanics only. A same-model long-horizon LLM OFF/current-ACE-S/hybrid A/B/C remains required for claims about actual instruction/architecture forgetting.