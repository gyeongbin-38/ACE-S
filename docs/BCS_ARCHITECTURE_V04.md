# ACE-S v0.4 Candidate Architecture — Bounded Context Scheduler

Status: experimental architecture snapshot. Do not treat synthetic controller benchmarks as end-to-end LLM quality evidence.

## Core thesis

ACE-S should minimize total context cost to a sufficient answer without making quality depend on a large monolithic rulebook or an aggressively predictive early-exit controller.

The controller should first exploit facts it can **prove**, then facts it can **bound**, then exact typed evidence it can **certify**. Only after these reductions should uncertain candidate value be estimated. If no calibrated risk certificate exists, the uncertain frontier falls back to the conservative evaluation budget rather than forcing an early stop.

**Prove before Predict.**

## Main loop

```text
TaskSpec
  ↓
Tiny Task / Constraint Parse
  ↓
Epistemic State
  ↓
SUFFICIENT? ── yes ──→ STOP
  │ no
  ▼
Candidate Generator
  ↓
Hard Feasibility / Exact Certificates
  ↓
Structural Dominance Pruning
  ↓
Feasible-Plan Bound / Cost-Floor Pruning
  ↓
Context Action Frontier
  ↓
Conservative Value Evaluation
  ↓
Execute ONE action
  ↓
Observe / Normalize Evidence
  ├─ typed + certificate-capable → Evidence Certificate
  └─ semantic / uncertified       → selected full evidence
  ↓
Update Controller + Worker-Visible State
  ↓
Lifecycle Decision
  ↓
STOP or REPLAN
```

The number of logical stages is not the number of policy modules physically loaded. The runtime should load only the tiny kernel and the policy/certificate definitions required by the current action.

## Certificate-strength ordering

Optimization should be ordered by the strength of the evidence supporting it:

```text
Level 0  Sufficient now
         → STOP

Level 1  Exact structural certificate
         → deterministic elimination / reuse

Level 2  Valid cost or feasibility bound
         → cost-floor pruning

Level 3  Exact typed outcome + provenance certificate
         → compact worker-visible evidence

Level 4  Calibrated statistical/risk certificate
         → optional adaptive compute / early stop

Level 5  No certificate
         → conservative/full frontier evaluation
```

A weaker certificate must never unlock a more aggressive optimization than a stronger one.

## Architectural roles

### Tiny Task Interpreter

Extract only the task goal and hard obligations needed to decide whether more context is required:

- exactness requirements,
- freshness requirements,
- provenance requirements,
- quality/safety invariants,
- whether the current context is already sufficient.

Do not load all specialist policies for awareness.

### Epistemic State Store

Maintain separate controller and worker-visible epistemic states.

```ts
type EpistemicState = {
  knownClaims: Claim[];
  openQuestions: Question[];
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

type WorkerVisibleState = {
  evidence: EvidenceRef[];
  certifiedOutcomes: EvidenceCertificate[];
  unresolvedMaterialQuestions: string[];
};
```

The controller knowing a fact does not automatically mean the worker may act on it. Worker-visible sufficiency must be satisfied independently.

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

Therefore `source × fidelity` is a schedulable action. Intermediate fidelities may be skipped when a lower or higher fidelity is provably the better candidate.

### Exact Pruning Plane

Before any stochastic or model-based candidate evaluation, remove actions only when the controller has a valid certificate.

#### Structural dominance

Action `A` may be removed when another action `B` is no more expensive and `B`'s observation partition provably refines `A` on the current state.

Do not use semantic similarity as a dominance proof.

#### Cost-floor pruning

If the runtime has a feasible complete-plan upper bound `U`, an action whose unavoidable immediate/lower-bound cost already exceeds `U` may be removed.

If no valid complete-plan bound is available, abstain. Do not manufacture an upper bound from a heuristic guess.

### Context Action Frontier

After exact pruning, only the surviving frontier is eligible for uncertain value evaluation.

For a candidate action `a`, the conceptual objective remains:

```text
Q(a) = measured_immediate_cost(a)
     + estimated_future_cost_to_sufficiency(a)
     + risk_penalty(a)
```

Measured quantities should remain runtime measurements whenever possible:
- token/byte size,
- local/remote class,
- tool/RPC cost,
- retrieval depth,
- latency,
- cache status,
- reacquisition cost.

Do not ask the LLM to estimate a quantity the runtime can measure directly.

### Conservative uncertain plane

A fixed or otherwise conservative evaluation budget is the default when candidate value is uncertain.

Empirical early-stop mechanisms are not architecture defaults merely because they reduce average sampling. Development and sealed synthetic tests repeatedly showed that topology heuristics, pilot agreement, and sequential racing can preserve mean/P95 behavior while still producing rare large environment-cost regressions.

Adaptive compute may be reintroduced only behind a calibrated risk certificate with predeclared tail-risk limits. Until then:

```text
certificate available?  yes → bounded optimization
certificate unavailable? no  → conservative frontier evaluation
```

### Typed Evidence Certificate

Acquisition and worker exposure are separate concerns only when the runtime can preserve worker knowledge exactly.

A structured result may be certificate-compressed only when all are true:

1. the action is explicitly typed and certificate-capable,
2. the controller has observed the exact typed outcome,
3. the certificate carries that exact outcome and a source/provenance reference,
4. applying the certificate produces the same worker-visible epistemic update as full structured exposure,
5. semantic/free-text evidence is never certificate-compressed,
6. answer termination still requires both controller and worker-visible sufficiency.

Conceptual certificate:

```ts
type EvidenceCertificate<T> = {
  schema: string;
  outcome: T;               // exact typed observation
  sourceRef: string;        // provenance / raw recovery ref
  validatorRef?: string;    // optional schema/adapter validator
};
```

This is not ordinary summarization. If exact equivalence cannot be established, expose the required evidence normally.

### Evidence Normalizer

Convert raw/tool outputs to compact recoverable EvidencePackets. Preserve exact references to raw evidence in CAS/artifact storage.

For typed certificate-capable evidence, preserve both:
- the raw recoverable source,
- the exact typed outcome/provenance certificate.

### Lifecycle Scheduler

Retention is part of the same scheduling problem. Candidate lifecycle actions include:
- KEEP_RAW
- KEEP_ABSTRACT
- OFFLOAD
- DROP

Consider:
- expected reuse,
- exactness probability,
- residency cost,
- compaction cost,
- reacquisition cost,
- remaining work.

Receding-horizon lifecycle planning has stronger synthetic OOD support than fixed retention heuristics, but it remains synthetic lifecycle economics rather than end-to-end LLM-quality evidence.

### STOP as an action

STOP is legal only when current answer/evidence obligations are satisfied or when an explicit risk model certifies the residual risk within the task's quality budget.

Do not interpret a cheap `Q(STOP)` estimate as permission to terminate when material evidence obligations remain unresolved.

## Runtime boundaries

```text
Agent
├─ Perception
│  ├─ tiny task parsing
│  └─ candidate generation
├─ ACE-S Control Plane
│  ├─ controller epistemic state
│  ├─ worker-visible state
│  ├─ exact certificate / bound checks
│  ├─ context action frontier
│  ├─ conservative value evaluator
│  ├─ typed evidence certificates
│  ├─ lifecycle scheduler
│  └─ sufficiency / stop gate
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

ACE-S is not the repository reader, web search engine, vector database, or memory backend. It is the control plane deciding what context action to take next, what evidence representation is legal, and what context to retain.

## Worker contract

The worker should receive only:
- task/goal,
- selected evidence,
- exact typed certificates when legal,
- compact current state,
- a small compiled action/procedure capsule when needed.

The worker should not receive the full routing, retrieval, retention, certificate, or fidelity rulebook by default.

## Policy loading

**Policy is context too.** Apply progressive disclosure to ACE-S itself.

Examples:
- structural-pruning policy is loaded only when comparable action metadata exists,
- cost-floor policy is loaded only when a feasible-plan bound can exist,
- evidence-certificate policy is loaded only for typed certificate-capable tool results,
- lifecycle policy is loaded only for long-horizon retention decisions,
- risk-calibrated early-stop policy remains unloaded unless such a certificate system is explicitly enabled.

## Measurement discipline

Do not equate rollout sample count with real expensive-model compute.

The synthetic evaluators memoize continuation values, so repeated rollout draws can hit cached states. Benchmark reports should distinguish at least:

1. algorithmic sample draws,
2. unique/cache-aware value evaluations,
3. tool/RPC calls,
4. worker-visible tokens/bytes,
5. measured wall-clock latency in a real runtime.

Synthetic accounting audits are useful for controller mechanics but do not substitute for measured Web GPT/Codex/runtime latency.

## Current evidence boundary

Stronger synthetic evidence currently supports:
- structural dominance with exact-optimum preservation on sealed synthetic OOD,
- cost-floor pruning with abstention when no valid bound exists,
- typed evidence certificates under exact typed-state equivalence and provenance constraints,
- receding-horizon lifecycle retention versus a fixed retention heuristic.

Synthetic evidence currently does **not** justify architecture-default adaptive early stopping. Multiple post-freeze OOD tests exposed rare catastrophic regressions despite favorable average metrics.

None of these controller experiments establish end-to-end frontier-model answer-quality gains. A real-runtime benchmark must measure final answer quality, evidence correctness, tokens/bytes, tool calls, cache-aware compute, and latency together.
