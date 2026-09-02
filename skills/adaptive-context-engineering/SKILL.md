---
name: adaptive-context-engineering
description: Use this skill when a task may suffer from too much, too little, stale, conflicting, poorly scoped, or prematurely compressed context: repository investigation, long documents, deep research, changing facts, multi-step work, handoffs, or explicit context/token optimization. ACE-S extracts a small set of context signals, derives a primary domain plus cross-cutting modifiers, chooses the lowest sufficient fidelity, and expands only when evidence is insufficient. Do not use for simple one-shot questions, casual conversation, creative writing, or tasks already solvable from current context without retrieval.
license: MIT
metadata:
  version: "0.3.0-alpha"
  methodology: "quality-first layered context decision control"
  benchmark: "popular-repo-replay-v0.2 + routerbench-v0.1"
---

# Adaptive Context Engineering

Optimize **successful-task quality per unit of context**, not token count in isolation.

ACE-S is a small context decision controller. Keep the core policy small; load specialist guidance only after the relevant signals are active.

## L0. Activation

Before retrieving or loading more material, decide:

- `DIRECT` — current context is sufficient; solve without new retrieval.
- `ACTIVE` — context selection materially affects correctness, completeness, freshness, provenance, or future steps.
- `UNCERTAIN` — one bounded check is needed before deciding.

Ask:

1. Is the current context already sufficient to answer reliably?
2. Would additional retrieval materially reduce uncertainty or prevent an important error?

**No retrieval is a valid action.** Do not activate ACE-S merely because tools or large context are available.

## L1. Extract signals, not actions

Record only facts that matter to context control. Prefer deterministic/observable signals when available; use semantic judgment only for ambiguous signals.

Typical signals:

```yaml
repository_present: boolean
long_document_present: boolean
external_research_requested: boolean
freshness_sensitive: boolean
conflicting_state_possible: boolean
exact_evidence_required: boolean
multi_step_task: boolean
handoff_expected: boolean
large_recoverable_output: boolean
current_context_sufficient: boolean | uncertain
```

Do not jump directly from one keyword to a final route. Signals describe the task; policy decides what to do with them.

## L2. Project signals into policy dimensions

Use one **primary domain** and zero or more **modifiers**.

Primary domain:

- `GENERAL` — no specialist source structure dominates.
- `CODE` — symbols, files, dependencies, tests, commits, or change impact dominate.
- `LONG_DOCUMENT` — information is primarily inside one or more large documents.
- `RESEARCH` — multi-source external evidence or synthesis dominates.
- `STATE` — resolving current vs superseded/conflicting state dominates.

Modifiers are cross-cutting and may coexist:

- `TEMPORAL` — freshness/version/date can change the answer.
- `EVIDENCE_CRITICAL` — exact wording, provenance, corroboration, or auditability matters.
- `PLAN_AWARE` — later steps need state gathered now.
- `TOOL_DISCOVERY` — the needed capability/source is not yet known.

Do not force a mixed task into one overloaded route. Example:

```yaml
primary_domain: CODE
modifiers: [RESEARCH, TEMPORAL, PLAN_AWARE]
```

If the primary domain is uncertain, keep top candidates internally and choose the specialist guidance that constrains the next retrieval step most directly. Do not load every candidate reference.

## L3. Choose the next context action

Choose the **lowest sufficient fidelity** and the **narrowest useful scope**.

Preferred scope order when applicable:

1. exact owner/path/symbol/entity/index
2. lexical or structured lookup
3. local dependency / hierarchy neighborhood
4. task-aware or semantic retrieval
5. broad search only as fallback

Resolution levels:

1. `INDEX` — metadata, TOC, path/symbol map, headings, source list.
2. `SUMMARY` — compact orientation when exact details are not yet needed.
3. `EXTRACT` — relevant section, code region, record, or source passage.
4. `RAW` — exact source truth.

Choose the lowest level that can safely answer the current subproblem. **Do not treat the ladder as a mandatory sequence.** Skip directly to `RAW` when exact contracts, quotations, precise numbers, changed requirements, or disputed facts require it.

Recommended actions:

`DIRECT | FETCH | EXPAND | REOPEN_RAW | PIN | OFFLOAD | COMPACT | STOP`

For a picker/decision, prefer categorical commitments over vague numeric scoring. Example: classify `unresolved_conflict=true/false` and let explicit policy decide `EXPAND` vs `STOP`.

## Specialist guidance

Load only guidance implied by the projection:

- `CODE` → `references/coding.md`
- `LONG_DOCUMENT` → `references/long-document.md`
- `RESEARCH` → `references/research.md`
- `STATE` or `TEMPORAL` → `references/temporal.md`
- `PLAN_AWARE` → `references/plan-aware.md`
- `EVIDENCE_CRITICAL` → `references/evidence-and-provenance.md`
- large histories/tool output or uncertain fidelity → `references/resolution-ladder.md`

`TOOL_DISCOVERY` is a modifier, not a specialist route: discover the smallest capability/source set needed for the already identified context problem.

Do not load unrelated reference files.

## L4. Sufficiency and retention

After each retrieval round, evaluate categorical facts:

```yaml
material_claims_covered: boolean
unresolved_material_conflict: boolean
freshness_verified: boolean | not_required
exact_evidence_available: boolean | not_required
likely_to_change_answer: boolean
reconstruction_needed: boolean
```

A conservative stop policy is:

```text
STOP when
material_claims_covered == true
AND unresolved_material_conflict == false
AND freshness_verified != false
AND exact_evidence_available != false
AND likely_to_change_answer == false
```

Otherwise take **one narrow `EXPAND` step**. Re-enter at L3 after retrieval; do not restart the whole classification pipeline unless the task itself changed materially.

For long-horizon work:

- `PIN` future-critical constraints, decisions, state, and evidence references.
- `OFFLOAD` large recoverable logs/tool output behind references.
- `COMPACT` completed exploration at semantic task boundaries.
- Preserve a route back to raw evidence.
- Track avoidable reconstruction/reacquisition when dropped context has to be fetched again.

## Context hygiene

- Separate objective, constraints, current state, decisions, unresolved questions, and evidence references from raw history.
- Treat summaries as **views, not source of truth**.
- Keep superseded state distinguishable from current state.
- Do not forward large recoverable tool output merely because it already exists.
- Preserve exact contracts by reference rather than rewriting them from memory.

## Final verification

Before answering or acting:

1. Re-check fidelity-critical facts against raw evidence.
2. Confirm the answer uses current, not superseded, state.
3. Make material uncertainty explicit.
4. Confirm important summaries/aggregates remain recoverable to source truth.
5. Do not claim an optimization improved quality unless measured against a baseline.

Default priority:

**correctness and completeness → recoverability/provenance → context efficiency → latency.**
