# Experimental Context Contracts

> **Status:** experimental for the v0.4 development line. These are trace/contracts for implementers, not a requirement that every field be placed in every model prompt.

ACE-S is a portable context-policy skill. The contracts below make **selective policy loading, recovery, evidence, and sufficiency** observable without requiring a particular backend.

## 1. ContextIntent — coarse recognition only

Do not fully classify the task at entry.

```yaml
ContextIntent:
  activation: DIRECT | ACTIVE | UNCERTAIN
  primary_candidate: CODE | DOCUMENT | RESEARCH | STATE | GENERAL | null
  backup_candidate: CODE | DOCUMENT | RESEARCH | STATE | GENERAL | null
  reason: string
```

### Invariants

- `DIRECT` requires no candidate policy.
- Keep at most one backup candidate.
- Candidates are **where to look next**, not a complete description of the whole task.
- Do not predict every modifier at entry.

## 2. PolicyLoadState — policy is context too

```yaml
PolicyLoadState:
  loaded_manifests: [string]
  loaded_specialists: [string]
  active_domain: CODE | DOCUMENT | RESEARCH | STATE | GENERAL | null
  active_modifiers: [TEMPORAL | EVIDENCE | TOOLS | RETENTION]
  backup_candidate: string | null
  recovery_count: integer
  last_progress: string | null
```

### Invariants

- A manifest load does not imply its specialist must be loaded if the manifest mismatches.
- Do not load every manifest or specialist to improve confidence.
- Modifier policies are loaded lazily when the current subproblem makes them material.
- `recovery_count` records wrong-first-candidate recovery rather than hiding it as a perfect initial classification.

## 3. Local ContextSignals — optional, policy-scoped

Signals are useful **inside the currently loaded policy**, but ACE-S no longer requires one global all-domain signal vector at task start.

Example:

```yaml
ContextSignals:
  scope: CODE
  exact_symbol_known: true | false | uncertain
  callers_needed: true | false | uncertain
  tests_needed: true | false | uncertain
  branch_freshness_material: true | false | uncertain
```

A research or document policy may define different local signals. Prefer categorical observations over vague numeric scoring.

## 4. ContextDecision — one next action

```yaml
ContextDecision:
  action: DIRECT | FETCH | EXPAND | SWITCH_POLICY | REOPEN_RAW | PIN | OFFLOAD | COMPACT | STOP
  policy: string | null
  target: string | null
  resolution: INDEX | SUMMARY | EXTRACT | RAW | null
  current_sufficiency: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  next_expansion: string | null
  stop_reason: string | null
```

### Invariants

- `DIRECT` and `STOP` introduce no new retrieval target.
- `SWITCH_POLICY` is bounded recovery, not permission to load all remaining policies.
- `RAW` is fidelity-critical source truth, not the default.
- `next_expansion` names one narrow action.

## 5. EvidencePacket

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

- Exact or fidelity-critical evidence remains recoverable from `locator`.
- Summaries never become their own source of truth.
- Version/revision/date belongs in `source_state` when it can change the answer.

## 6. SufficiencyReport

```yaml
SufficiencyReport:
  status: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  material_claims_covered: boolean
  unresolved_material_conflict: boolean
  freshness_verified: true | false | not_required
  exact_evidence_available: true | false | not_required
  likely_to_change_answer: boolean
  next_expansion: string | null
```

A conservative stop rule is:

```text
status == SUFFICIENT
AND material_claims_covered == true
AND unresolved_material_conflict == false
AND freshness_verified != false
AND exact_evidence_available != false
AND likely_to_change_answer == false
```

Do not use token count alone as a stop condition.

## 7. RetentionDecision and HandoffState

These are optional and should not be created for ordinary one-shot tasks.

```yaml
RetentionDecision:
  pin: [string]
  offload: [string]
  compact: [string]
  evict: [string]
  reason: string
```

```yaml
HandoffState:
  objective: string
  constraints: [string]
  decisions:
    - decision: string
      evidence_refs: [string]
  current_state: [string]
  artifacts: [string]
  open_questions: [string]
  next_action: string
  do_not_repeat: [string]
```

Track reacquisition when evicted/offloaded information must be fetched or reconstructed again.

## 8. WorkingContext

```yaml
WorkingContext:
  objective: string
  constraints: [string]
  current_state: [string]
  decisions: [string]
  evidence_refs: [string]
  unresolved: [string]
```

This projection contains what the **next model call needs**, not the entire event history or every policy ever considered.

## 9. Progressive control loop

```text
Task
 ↓
Tiny Kernel: DIRECT / ACTIVE / UNCERTAIN
 ↓
Coarse candidate (1 + optional backup)
 ↓
Manifest index
 ↓
ONE candidate manifest
 ├─ mismatch → bounded SWITCH_POLICY
 └─ fits
      ↓
ONE specialist policy
      ↓
minimal context retrieval
      ↓
SufficiencyReport
 ├─ sufficient → STOP
 └─ insufficient
      ↓
next narrow action
      ├─ same policy → FETCH / EXPAND
      └─ new concern becomes material → load ONE lazy modifier/domain policy
```

Ordinary retrieval loops re-enter at the current policy/action state. Re-run coarse recognition only when the task materially changes or the selected policy cannot make progress.

## 10. What is intentionally absent

ACE-S does not prescribe:

- vector database or embedding model;
- memory/storage engine;
- prompt format;
- agent framework;
- graph database;
- learned vs deterministic candidate selector;
- mandatory global classifier over all policies.

## 11. Evaluation requirements

Do not treat policy-selection accuracy alone as the objective. Evaluate:

- verified task success / final answer quality;
- initial-candidate recall;
- wrong-first-candidate recovery rate;
- specialist manifests loaded per task;
- irrelevant policy-load rate;
- policy bytes/tokens loaded;
- false stop / unnecessary expansion;
- context retrieval volume and rounds;
- reacquisition overhead;
- provenance recoverability.

Controller-mechanics benchmarks must be labeled separately from real-model routing and end-to-end agent benchmarks.
