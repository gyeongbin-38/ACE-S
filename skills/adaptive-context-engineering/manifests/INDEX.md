# ACE-S Policy Manifest Index

Read this index only after the ACE-S kernel decides context control is `ACTIVE` or `UNCERTAIN`.

This file is a **directory, not the policy itself**. The first decision is whether a specialized source domain clearly dominates the next context step. Do not force specialization merely because ACE-S is active.

## Entry mode

### `SPECIALIZED`

Use when one source structure clearly dominates the next retrieval.

| Candidate | Use when the next useful context is mainly about | Manifest |
|---|---|---|
| `CODE` | repository structure, symbols, implementations, callers, tests, commits, or change impact | `manifests/code.md` |
| `DOCUMENT` | one or more long supplied documents, manuals, policies, papers, books, or specifications | `manifests/document.md` |
| `RESEARCH` | evidence must be gathered or synthesized across external sources | `manifests/research.md` |
| `STATE` | current vs superseded/conflicting state must be resolved | `manifests/state.md` |

Choose **one specialized candidate first**. Keep at most one backup only when the specialized boundary is genuinely ambiguous.

### `GENERIC`

Use `manifests/generic.md` when context selection matters but no specialized source domain clearly dominates yet.

GENERIC is not a fifth specialist. It is a low-commitment entry mode for locating one source/capability, handling working context, or performing one bounded inspection before specialization is justified.

Do not invent a specialized label just to avoid GENERIC.

## Lazy modifiers

Do not classify every modifier up front. Open one only when the current subproblem makes it material.

| Modifier | Material when | Manifest |
|---|---|---|
| `TEMPORAL` | the answer could change with date, version, revision, release, or freshness | `manifests/temporal.md` |
| `EVIDENCE` | exact wording, provenance, corroboration, or auditability materially affects the answer | `manifests/evidence.md` |
| `TOOLS` | the capability/source needed to inspect the context is not yet known | `manifests/tools.md` |
| `RETENTION` | later steps, handoffs, or large recoverable outputs create a keep/offload decision | `manifests/retention.md` |

## Utility policy

If the **fidelity choice itself** is uncertain after the relevant entry/domain policy is loaded, read `references/resolution-ladder.md`. Do not load it by default.

## Bounded recovery and specialization

If a specialized manifest clearly mismatches the task or produces no useful next action:

1. stop loading that branch;
2. try the single retained backup if one exists;
3. otherwise return to GENERIC entry instead of scanning all specialists;
4. specialize later only when newly observed structure justifies one domain.

If GENERIC makes no progress, change the concrete target/capability once; do not compensate by loading every policy.
