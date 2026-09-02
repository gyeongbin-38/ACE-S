# Experimental Context Contracts

> **Status:** experimental in `v0.3.x`; names and fields are not yet a stable runtime API.

ACE-S is primarily a skill/policy, but runtime implementers need a small shared vocabulary. These contracts describe the **minimum state worth passing between context selection, retrieval, execution, and handoff** without forwarding the entire transcript.

They are deliberately backend-neutral.

## 1. ContextDecision

Represents one context-control decision.

```yaml
ContextDecision:
  route: DIRECT | CODE | LONG_DOCUMENT | TEMPORAL | RESEARCH | PLAN_AWARE | EVIDENCE
  target: string | null
  resolution: INDEX | SUMMARY | EXTRACT | RAW | null
  evidence_needed: [string]
  current_sufficiency: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  next_expansion: string | null
  stop_reason: string | null
```

### Invariants

- `DIRECT` should not carry a retrieval target unless the host already supplied evidence.
- `RAW` is appropriate for fidelity-critical facts, not as a default resolution.
- `next_expansion` should name one narrow expansion step, not “search everything”.
- `SUFFICIENT` requires a non-empty `stop_reason` in implementations that persist decisions.

## 2. EvidencePacket

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

- `EXACT` evidence must remain recoverable from `locator`.
- A transformed summary must not become its own source of truth.
- `source_state` should carry a version, revision, commit, date, or equivalent when staleness could change the answer.
- Conflicting packets should coexist until a controlling source is justified; do not silently overwrite one.

## 3. HandoffState

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
- `current_state` must not merge superseded and current values.
- `do_not_repeat` is for completed/rejected exploration that would otherwise be needlessly rediscovered.
- Exact contracts should be referenced, not rewritten from memory into lossy prose.

## 4. SufficiencyReport

Makes the stop condition explicit.

```yaml
SufficiencyReport:
  status: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  material_claims:
    - claim: string
      evidence_ref: string | null
      status: SUPPORTED | MIXED | UNSUPPORTED | STALE
  unresolved_conflicts: [string]
  missing_evidence: [string]
  likely_to_change_answer: boolean
  next_expansion: string | null
```

### Stop rule

A conservative implementation may stop when:

```text
status == SUFFICIENT
AND likely_to_change_answer == false
AND unresolved_conflicts contains no material conflict
```

Do not use token count alone as the stop rule.

## 5. WorkingContext

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

The projection should contain **what the next model call needs**, not every event that produced it.

Raw history, large logs, document bodies, repository files, and full tool output should remain externally recoverable whenever the host runtime supports it.

## 6. Recommended controller actions

These action names are intentionally small and composable:

```text
DIRECT       solve with current context
ROUTE        select a specialist policy
FETCH        retrieve one targeted source/scope
EXPAND       widen scope or fidelity one step
PIN          retain future-critical state
OFFLOAD      move large raw material behind a reference
REOPEN_RAW   verify a fidelity-critical fact
COMPACT      replace completed exploration with state + refs
STOP         declare the context sufficient
```

These are policy semantics, not a required transport protocol.

## 7. Minimal control loop

```text
Task
 ↓
ContextDecision
 ↓
FETCH / EXPAND / DIRECT
 ↓
EvidencePacket(s)
 ↓
WorkingContext
 ↓
SufficiencyReport
 ├─ sufficient → REOPEN_RAW if needed → STOP
 └─ insufficient → one narrow next_expansion → repeat
```

For multi-step tasks, emit or update `HandoffState` at semantic boundaries.

## 8. What is intentionally absent

The contracts do not prescribe:

- vector database vendor;
- embedding model;
- graph database;
- memory server;
- prompt format;
- agent framework;
- storage engine;
- serialization format;
- learned vs deterministic controller.

ACE-S should be implementable over local files, web search, code graphs, databases, memory systems, or combinations of them.

## 9. Stabilization criteria

These contracts should not become a stable API until real-agent A/B evaluation shows that the fields are sufficient across multiple agent surfaces without encouraging unnecessary context growth.

Before stabilization, evaluate:

- whether fields are actually used downstream;
- whether exact/provenance-sensitive tasks remain recoverable;
- whether handoffs resume without rediscovery;
- whether controller decisions can be logged without leaking full raw context;
- whether the shape remains backend-neutral.
