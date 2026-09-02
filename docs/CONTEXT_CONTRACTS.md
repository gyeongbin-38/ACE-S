# Experimental Context Contracts

> **Status:** experimental in `v0.4.x`; names and fields are not yet a stable runtime API.

ACE-S is primarily a skill/policy. These contracts give runtime implementers a small shared vocabulary for passing context-control state without forwarding the full transcript. They are deliberately backend-neutral.

## 1. ContextSignals

Facts observed before policy is applied.

```yaml
ContextSignals:
  repository_present: boolean
  long_document_present: boolean
  external_research_requested: boolean
  freshness_sensitive: boolean
  conflicting_state_possible: boolean
  exact_evidence_required: boolean
  multi_step_task: boolean
  handoff_expected: boolean
  large_recoverable_output: boolean
  current_context_sufficient: true | false | uncertain
```

### Invariants

- Signals describe observable or semantically classified task properties; they do not prescribe actions.
- Prefer deterministic signals when available.
- Unknown/uncertain is valid when forcing a boolean would hide ambiguity.

## 2. ContextProjection

Transforms signals into policy dimensions.

```yaml
ContextProjection:
  activation: DIRECT | ACTIVE | UNCERTAIN
  primary_domain: GENERAL | CODE | LONG_DOCUMENT | RESEARCH | STATE
  secondary_domains: [GENERAL | CODE | LONG_DOCUMENT | RESEARCH | STATE]
  modifiers: [TEMPORAL | EVIDENCE_CRITICAL | PLAN_AWARE | TOOL_DISCOVERY]
  minimum_fidelity: INDEX | SUMMARY | EXTRACT | RAW
  risk: LOW | MEDIUM | HIGH
```

### Invariants

- `primary_domain` answers where/what kind of context dominates the next retrieval decision.
- `modifiers` are cross-cutting constraints and may coexist.
- `TEMPORAL`, `EVIDENCE_CRITICAL`, and `PLAN_AWARE` are modifiers rather than mutually exclusive primary routes.
- Keep `secondary_domains` bounded; implementations should not load every candidate specialist policy.

## 3. ContextDecision

Represents one controller action after projection.

```yaml
ContextDecision:
  action: DIRECT | FETCH | EXPAND | REOPEN_RAW | PIN | OFFLOAD | COMPACT | STOP
  target: string | null
  resolution: INDEX | SUMMARY | EXTRACT | RAW | null
  evidence_needed: [string]
  current_sufficiency: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  next_expansion: string | null
  stop_reason: string | null
```

### Invariants

- `DIRECT` and `STOP` should not introduce a new retrieval target.
- `RAW` is for fidelity-critical facts, not the default.
- `next_expansion` names one narrow expansion step, never “search everything”.
- `SUFFICIENT` requires a non-empty `stop_reason` when persisted.
- Detection/classification should not be hidden inside an opaque numeric score when categorical features can be logged instead.

### Compatibility note

`v0.3.x` used one overloaded `route` enum (`CODE`, `TEMPORAL`, `PLAN_AWARE`, etc.). In `v0.4.x`, that concept is intentionally decomposed into `primary_domain + modifiers + action`. Runtime adapters may translate the old enum during migration, but new traces should use the layered shape.

## 4. EvidencePacket

Represents source-backed evidence that can survive compaction.

```yaml
EvidencePacket:
  claim: string
  source: string
  locator: string
  source_state: string | null
  evidence: string
  fidelity: EXACT | EXTRACTIVE | LOSSY
  authority: PRIMARY | AUTHORITATIVE_SECONDARY | SECONDARY | COMMUNITY
  status: SUPPORTS | CONTRADICTS | PARTIAL
  caveat: string | null
```

### Invariants

- `EXACT` evidence remains recoverable from `locator`.
- A transformed summary never becomes its own source of truth.
- `source_state` carries version/revision/commit/date when staleness can change the answer.
- Conflicting packets coexist until a controlling source is justified.

## 5. HandoffState

Represents the smallest useful state needed to resume a multi-step task.

```yaml
HandoffState:
  objective: string
  completed: [string]
  constraints: [string]
  decisions:
    - decision: string
      rationale: string
      evidence_refs: [string]
  artifacts: [string]
  current_state: [string]
  open_questions: [string]
  next_action: string
  do_not_repeat: [string]
```

### Invariants

- `constraints` contains only requirements that are still binding.
- `current_state` does not merge superseded and current values.
- `do_not_repeat` records completed/rejected exploration that would otherwise be needlessly reacquired.
- Exact contracts are referenced rather than reconstructed from lossy prose.

## 6. SufficiencyReport

Makes the stop condition explicit using categorical commitments.

```yaml
SufficiencyReport:
  status: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  material_claims_covered: boolean
  unresolved_material_conflict: boolean
  freshness_verified: true | false | not_required
  exact_evidence_available: true | false | not_required
  likely_to_change_answer: boolean
  reconstruction_needed: boolean
  material_claims:
    - claim: string
      evidence_ref: string | null
      status: SUPPORTED | MIXED | UNSUPPORTED | STALE
  missing_evidence: [string]
  next_expansion: string | null
```

### Stop rule

A conservative implementation may stop when:

```text
status == SUFFICIENT
AND material_claims_covered == true
AND unresolved_material_conflict == false
AND freshness_verified != false
AND exact_evidence_available != false
AND likely_to_change_answer == false
```

Do not use token count alone as the stop rule.

## 7. RetentionDecision

Optional long-horizon context policy.

```yaml
RetentionDecision:
  pin: [string]
  offload: [string]
  compact: [string]
  evict: [string]
  reason: string
```

Track reacquisition when evicted/offloaded state must be reconstructed or fetched again. This distinguishes genuine context efficiency from hidden interaction cost.

## 8. WorkingContext

A bounded projection consumed by the solver/agent.

```yaml
WorkingContext:
  objective: string
  constraints: [string]
  current_state: [string]
  decisions: [string]
  evidence_refs: [string]
  artifacts: [string]
  unresolved: [string]
```

The projection contains **what the next model call needs**, not every event that produced it.

Raw history, large logs, document bodies, repository files, and full tool output should remain externally recoverable whenever the host supports it.

## 9. Minimal layered control loop

```text
Task
 ↓
Activation
 ↓
ContextSignals
 ↓
ContextProjection
 ↓
ContextDecision
 ↓
FETCH / EXPAND / DIRECT / REOPEN_RAW
 ↓
EvidencePacket(s) + WorkingContext
 ↓
SufficiencyReport + optional RetentionDecision
 ├─ sufficient → STOP
 └─ insufficient → one narrow next_expansion → ContextDecision
```

Re-enter at the decision layer after ordinary retrieval. Re-run signal extraction/projection only when the task or controlling state changed materially.

## 10. What is intentionally absent

The contracts do not prescribe:

- vector database vendor;
- embedding model;
- graph database;
- memory server;
- prompt format;
- agent framework;
- storage engine;
- serialization format;
- learned vs deterministic classifier/controller.

ACE-S should work over local files, web search, code graphs, databases, memory systems, or combinations of them.

## 11. Stabilization criteria

Do not freeze these contracts until real-agent A/B evaluation shows that the fields are sufficient across multiple agent surfaces without encouraging unnecessary context growth.

Before stabilization, evaluate:

- activation precision/recall;
- primary-domain accuracy;
- modifier precision/recall;
- action and resolution accuracy;
- early-stop and late-stop failures;
- reacquisition overhead;
- exact/provenance recoverability;
- handoff resume quality;
- backend neutrality;
- whether every persisted field earns its context/storage cost.
