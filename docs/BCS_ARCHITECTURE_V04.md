# ACE-S v0.4 Candidate Architecture — Bounded Context Scheduler

Status: experimental architecture snapshot. Do not treat synthetic controller benchmarks as end-to-end LLM quality evidence.

## Core thesis

ACE-S should minimize expected total cost to a sufficient answer, rather than teach the worker model a large set of context-engineering rules.

Given the current epistemic state, generate candidate context actions, estimate measurable immediate cost plus bounded future cost-to-go, execute one action, observe, update state, and replan.

## Main loop

```text
TaskSpec
  ↓
Epistemic State
  ↓
Candidate Generator
  ↓
Cost / Outcome Estimator
  ↓
Bounded Rollout (K≈4–8)
  ↓
Action Selector
  ↓
Execute ONE action
  ↓
Observe / Normalize Evidence
  ↓
Update Epistemic State
  ↓
Lifecycle Decision
  ↓
STOP or REPLAN
```

## Architectural roles

### Task Interpreter
Extract goal, invariants, quality floor, exactness/freshness/provenance constraints. Do not load specialist policies just for awareness.

### Epistemic State Store
Track known claims, open questions, hypotheses, conflicts, hard evidence requirements, context inventory, and sufficiency state.

```ts
type EpistemicState = {
  knownClaims: Claim[];
  openQuestions: Question[];
  hypotheses: Hypothesis[];
  conflicts: Conflict[];
  constraints: {
    freshness: Requirement[];
    exactness: Requirement[];
    provenance: Requirement[];
  };
  contextInventory: ContextItem[];
  sufficiency: {
    answerable: boolean;
    unresolvedMaterialQuestions: string[];
    likelyToChangeAnswer: boolean;
  };
};
```

### Candidate Generator
Domain labels such as CODE, DOCUMENT, RESEARCH, or STATE are candidate-space hints, not hard execution routes.

Candidate actions may include:
- SEARCH
- FETCH
- EXPAND
- REOPEN
- VERIFY
- COMPACT
- OFFLOAD
- DROP
- STOP

Fidelity is an action parameter, not a mandatory ladder:
- INDEX
- SUMMARY
- EXTRACT
- RAW

Therefore `source × fidelity` is a schedulable action. The controller may skip intermediate fidelities when their expected value is low.

### Context Scheduler
For each candidate action `a`:

```text
Q(a) = measured_immediate_cost(a)
     + estimated_future_cost_to_sufficiency(a)
     + risk_penalty(a)
```

Use bounded receding-horizon rollout. Execute one action only, observe, and replan.

Do not ask the LLM to predict measurable costs when the runtime can measure them directly. Measurable cost features include token/byte size, tool-call cost, remote/local class, retrieval depth, latency, and reacquisition cost.

### Evidence Normalizer
Convert tool/raw outputs to compact recoverable EvidencePackets. Preserve exact references to raw evidence in CAS/artifact storage.

### Lifecycle Scheduler
Retention is part of the same scheduling problem. Candidate lifecycle actions include:
- KEEP_RAW
- KEEP_ABSTRACT
- OFFLOAD
- DROP

The decision should consider expected reuse, exactness probability, residency cost, compaction cost, reacquisition cost, and remaining work.

### STOP as an action
STOP should compete with retrieval/expansion actions.

```text
Q(STOP) = expected residual answer risk / quality loss
```

Continue only when another context action has lower expected total cost subject to quality/evidence constraints.

## Runtime boundaries

```text
Agent
├─ Perception
│  ├─ task parsing
│  ├─ tiny signal extraction
│  └─ candidate generation
├─ ACE-S Control Plane
│  ├─ epistemic state
│  ├─ measurable cost model
│  ├─ outcome/value estimator
│  ├─ bounded rollout scheduler
│  └─ sufficiency/stop gate
├─ Context Runtime
│  ├─ repo adapter
│  ├─ web adapter
│  ├─ file adapter
│  ├─ memory adapter
│  └─ artifact adapter
└─ Storage
   ├─ raw/CAS evidence
   ├─ compact state
   ├─ provenance index
   └─ traces
```

ACE-S is not the repository reader, web search engine, vector database, or memory backend. It is the control plane deciding what context action to take next, at what fidelity, and for how long to retain the result.

## Worker contract

The worker should receive only:
- task/goal
- selected evidence
- compact current state
- a small compiled action/procedure capsule when needed

The worker should not need the full routing, retrieval, retention, or fidelity rulebook.

## Design principle

**Policy is context too.** Apply progressive disclosure to ACE-S itself.

Quality first, efficiency second. Any optimization is acceptable only when final quality and evidence obligations are non-inferior to the baseline.

## Current evidence boundary

Synthetic experiments currently support the controller mechanics, including optional specialization, compiled policy capsules, unrestricted source×fidelity scheduling, bounded rollout, and lifecycle scheduling. They do not yet establish end-to-end frontier-model answer-quality gains.
