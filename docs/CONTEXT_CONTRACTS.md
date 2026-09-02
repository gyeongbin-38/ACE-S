# Experimental Context Contracts

> **Status:** experimental for the v0.4 development line. These are trace/contracts for implementers, not a requirement that every field be placed in every model prompt.

ACE-S is a portable context-policy skill. The contracts below make **optional specialization, selective policy loading, recovery, evidence, and sufficiency** observable without requiring a particular backend.

## 1. ContextIntent — coarse recognition only

Do not fully classify the task at entry. First decide whether specialization is justified at all.

```yaml
ContextIntent:
  activation: DIRECT | ACTIVE | UNCERTAIN
  specialization: SPECIALIZED | GENERIC | UNCERTAIN | null
  primary_candidate: CODE | DOCUMENT | RESEARCH | STATE | null
  backup_candidate: CODE | DOCUMENT | RESEARCH | STATE | null
  reason: string
```

### Invariants

- `DIRECT` requires `specialization=null` and no candidate policy.
- `GENERIC` requires no primary/backup specialist candidate.
- `SPECIALIZED` has one primary candidate and at most one backup.
- Candidates are **where to look next**, not a complete description of the whole task.
- Do not predict every modifier at entry.
- Do not force a specialized domain merely because context control is ACTIVE.

## 2. PolicyLoadState — policy is context too

```yaml
PolicyLoadState:
  entry_mode: GENERIC | SPECIALIZED | null
  loaded_manifests: [string]
  loaded_specialists: [string]
  active_domain: CODE | DOCUMENT | RESEARCH | STATE | null
  active_modifiers: [TEMPORAL | EVIDENCE | TOOLS | RETENTION]
  backup_candidate: string | null
  recovery_count: integer
  specialization_count: integer
  last_progress: string | null
```

### Invariants

- GENERIC entry loads no specialist by default.
- A specialized manifest load does not imply its specialist must be loaded if the manifest mismatches.
- Do not load every manifest or specialist to improve confidence.
- Modifier policies are loaded lazily when the current subproblem makes them material.
- `recovery_count` records wrong-first-candidate recovery rather than hiding it as a perfect initial classification.
- `specialization_count` makes late specialization visible; ordinary tasks should not bounce repeatedly between domains.

## 3. Local ContextSignals — optional, policy-scoped

Signals are useful **inside the currently loaded entry/domain policy**, but ACE-S does not require one global all-domain signal vector at task start.

Examples:

```yaml
ContextSignals:
  scope: GENERIC
  concrete_target_known: true | false | uncertain
  capability_known: true | false | uncertain
  working_history_is_target: true | false | uncertain
  specialized_structure_observed: true | false | uncertain
```

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
  action: DIRECT | FETCH | EXPAND | SPECIALIZE | SWITCH_POLICY | REOPEN_RAW | PIN | OFFLOAD | COMPACT | STOP
  policy: string | null
  target: string | null
  resolution: INDEX | SUMMARY | EXTRACT | RAW | null
  current_sufficiency: SUFFICIENT | INSUFFICIENT | UNCERTAIN
  next_expansion: string | null
  stop_reason: string | null
```

### Invariants

- `DIRECT` and `STOP` introduce no new retrieval target.
- `SPECIALIZE` is allowed only after observed context makes one specialized domain materially useful.
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
Does a specialized source domain clearly dominate?
 ├─ YES → SPECIALIZED
 │          ↓
 │       ONE candidate manifest (+ optional backup)
 │          ├─ mismatch → backup or GENERIC
 │          └─ fits → ONE specialist
 │
 └─ NO / not yet → GENERIC entry
                    ↓
               one concrete target/capability
                    ↓
               optional ONE lazy modifier
                    ↓
               bounded inspection
                    ├─ known domain emerges → SPECIALIZE once
                    └─ no domain needed → continue GENERIC

Both paths
  ↓
minimal context retrieval
  ↓
SufficiencyReport
  ├─ sufficient → STOP
  └─ insufficient → one narrow next action
```

Ordinary retrieval loops re-enter at the current policy/action state. Re-run coarse recognition only when the task materially changes or the current entry/domain policy cannot make progress.

## 10. Why GENERIC is not another domain

GENERIC does not claim expertise about artifacts, chat history, tables, media, or every future context type. It supplies only low-commitment mechanics:

- identify one next target;
- identify a needed capability if unknown;
- apply a lazy modifier only when material;
- specialize later if structure is actually observed.

This prevents every newly observed task family from becoming a permanent route.

## 11. What is intentionally absent

ACE-S does not prescribe:

- vector database or embedding model;
- memory/storage engine;
- prompt format;
- agent framework;
- graph database;
- learned vs deterministic candidate selector;
- mandatory global classifier over all policies;
- a fixed taxonomy for every possible artifact type.

## 12. Evaluation requirements

Do not treat policy-selection accuracy alone as the objective. Evaluate:

- verified task success / final answer quality;
- specialization precision: how often a specialist was actually warranted;
- initial-candidate recall when specialization is used;
- wrong-first-candidate recovery rate;
- late-specialization success from GENERIC;
- specialist manifests loaded per task;
- irrelevant policy-load rate;
- policy bytes/tokens loaded;
- false stop / unnecessary expansion;
- context retrieval volume and rounds;
- reacquisition overhead;
- provenance recoverability.

Controller-mechanics benchmarks, taxonomy-coverage stress tests, real-model routing, and end-to-end agent benchmarks must be reported separately.
