# ACE-S Policy Manifest Index

Read this index only after the ACE-S kernel decides that context control is `ACTIVE` or `UNCERTAIN`.

This file is a **directory, not the policy itself**. Pick the smallest plausible next policy. Do not open every manifest.

## Primary context domains

| Candidate | Use when the next useful context is mainly about | Manifest |
|---|---|---|
| `CODE` | repository structure, symbols, implementations, callers, tests, commits, or change impact | `manifests/code.md` |
| `DOCUMENT` | one or more long supplied documents, manuals, policies, papers, books, or specifications | `manifests/document.md` |
| `RESEARCH` | evidence must be gathered or synthesized across external sources | `manifests/research.md` |
| `STATE` | current vs superseded/conflicting state must be resolved | `manifests/state.md` |

Choose **one primary candidate first**. Keep at most one backup candidate when the boundary is genuinely ambiguous.

## Lazy modifiers

Do not classify every modifier up front. Open one only when the current subproblem makes it material.

| Modifier | Material when | Manifest |
|---|---|---|
| `TEMPORAL` | the answer could change with date, version, revision, release, or freshness | `manifests/temporal.md` |
| `EVIDENCE` | exact wording, provenance, corroboration, or auditability materially affects the answer | `manifests/evidence.md` |
| `TOOLS` | the capability/source needed to inspect the context is not yet known | `manifests/tools.md` |
| `RETENTION` | later steps, handoffs, or large recoverable outputs create a keep/offload decision | `manifests/retention.md` |

## Utility policy

If the **fidelity choice itself** is uncertain after a domain policy is loaded, read `references/resolution-ladder.md`. Do not load it by default.

## Bounded recovery

If the first candidate manifest clearly mismatches the task or produces no useful next action:

1. stop loading that branch;
2. try the single backup candidate if one was retained;
3. otherwise return to the task and form one new candidate;
4. never load all manifests “just in case”.
