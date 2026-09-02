# Plan-Aware Route

Use this route when the task has multiple stages, handoffs, delayed execution, or future steps that depend on information gathered now.

Context value depends on **future workflow utility**, not only relevance to the current prompt.

## 1. Define the decision horizon

Write the remaining workflow as a small sequence of states or milestones.

```text
Current step → next decision → implementation → verification → handoff
```

Do not model the entire future if only the next few steps affect retention.

## 2. Classify context by future utility

Separate working information into five buckets:

- **Invariants** — goals, constraints, policies, interfaces, acceptance criteria.
- **Decisions** — choices already made and the evidence/rationale needed to avoid reopening them accidentally.
- **Artifacts** — files, commits, datasets, prompts, outputs, IDs, links, or other recoverable work products.
- **Open state** — unresolved questions, risks, blockers, assumptions, experiments still pending.
- **Ephemeral exploration** — search trails, rejected candidates, verbose tool output, temporary reasoning scaffolding.

Retain the first four when they can affect a future step. Compact or discard the fifth once its useful result has been captured.

## 3. Estimate reconstruction cost

An item deserves retention when losing it would be expensive or impossible to reconstruct.

Useful questions:

- Would a later step have to repeat a costly search or tool call?
- Is this an exact contract, constraint, or decision boundary?
- Is the source likely to change or disappear?
- Does this explain why a tempting alternative was rejected?
- Can the item be re-read cheaply from a stable reference instead of kept verbatim?

Prefer **reference + compact state** over carrying raw history when recoverability is cheap.

## 4. Preserve decision provenance

A future agent or session should be able to distinguish:

```text
fact      → what the source says
inference → what we concluded from evidence
decision  → what we chose under constraints
```

Do not compact these into a single sentence when the distinction may matter later.

## 5. Compact at semantic boundaries

Compact when a meaningful unit of work finishes, not merely when a token threshold is crossed.

Good boundaries include:

- candidate discovery completed;
- architecture choice made;
- experiment finished;
- code change implemented;
- review completed;
- handoff about to occur.

At each boundary, replace exploration history with a state packet.

## 6. Handoff packet

Use a compact handoff shape for long workflows:

```text
HandoffState
- objective: current end goal
- completed: verified work already done
- constraints: still-binding requirements
- decisions: chosen options + concise rationale
- evidence_refs: recoverable sources/artifacts
- current_state: exact implementation/project state
- open_questions: unresolved items
- next_action: smallest useful next step
- do_not_repeat: work that does not need to be rediscovered
```

The handoff should be sufficient to resume work, but should not contain the full exploratory transcript.

## 7. Retention priority

When context pressure forces a choice, retain in this order:

1. safety/security/policy constraints;
2. exact contracts and acceptance criteria;
3. current state and irreversible decisions;
4. unresolved blockers and high-value evidence references;
5. reusable intermediate results;
6. low-cost reconstructable details;
7. conversational or exploratory residue.

## 8. Sufficiency for the next step

Before discarding context, ask:

- Can the next step execute without reopening completed work?
- Can important decisions be traced to evidence?
- Are current and superseded states distinguishable?
- Are exact constraints still represented losslessly or recoverably?

If not, retain or offload the missing item before compaction.

Future utility should influence retention, but never override exactness, provenance, or safety-critical evidence.
