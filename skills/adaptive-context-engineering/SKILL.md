---
name: adaptive-context-engineering
description: Use this skill when a task may fail because context is missing, excessive, stale, conflicting, poorly scoped, or prematurely compressed. ACE-S first decides whether more context is needed, then decides whether a specialist source domain clearly dominates. It loads only the smallest relevant entry policy, retrieves the narrowest useful context, and specializes, expands, or switches only when evidence justifies it. Do not use for simple one-shot tasks already solvable from supplied context.
license: MIT
metadata:
  version: "0.3.0-alpha"
  methodology: "quality-first progressive specialization and policy loading"
  benchmark: "popular-repo-replay-v0.2 + selective-policy-load-bench-v0.1"
---

# Adaptive Context Engineering

Optimize **successful-task quality per unit of context**.

ACE-S is a **small context-policy kernel**, not a rulebook that should be fully loaded on every task.

## 0. Sufficiency first

Before loading any policy or retrieving anything:

- `DIRECT` — current context is sufficient; solve now.
- `ACTIVE` — context selection materially affects correctness, completeness, freshness, provenance, or later work.
- `UNCERTAIN` — make one bounded check before deciding.

**No retrieval is a valid action.** Do not activate merely because tools, files, or long context are available.

## 1. Decide whether specialization is earned

If `ACTIVE` or `UNCERTAIN`, do **not** immediately force the task into a specialist route.

Ask only:

> Does one specialized source structure clearly dominate the **next useful context step**?

Then read `manifests/INDEX.md`.

- If **yes**, choose one specialized candidate. Keep at most one backup when genuinely ambiguous.
- If **no**, use the GENERIC entry mode. GENERIC is not a fifth specialist; it exists to locate the next source/capability or manage working context without inventing a false domain.
- If **uncertain**, prefer one cheap manifest/index-level check over loading several policies.

The goal of coarse recognition is to make the next context action cheap and recoverable, not to fully classify the whole task.

## 2. Progressive policy loading

Open only the selected entry manifest.

For a specialized entry, open only the specialist reference named by that manifest **after the manifest fits**.

For GENERIC entry, do not load a specialist by default. Identify one concrete next source/capability or working-context problem first.

Do **not** read all manifests or all specialist references “for awareness”.

Cross-cutting policies such as freshness, provenance, tool discovery, or retention are **lazy modifiers**. Load one only when the current subproblem makes that concern material.

Example:

```text
operational data task
  → no specialist clearly dominates
  → GENERIC entry
  → capability to inspect the artifact is unknown
  → TOOLS modifier
  → bounded inspection reveals repository code must change
  → CODE manifest
  → coding specialist
```

The architecture should emerge from the task as evidence is gathered; it should not be preloaded in full.

## 3. Retrieve the minimum useful context

Prefer the narrowest useful scope:

1. exact owner/path/symbol/entity/heading/source id/artifact;
2. structured or lexical lookup;
3. local dependency/hierarchy neighborhood;
4. task-aware semantic retrieval;
5. broad search only as fallback.

Use the lowest sufficient fidelity:

`INDEX → SUMMARY → EXTRACT → RAW`

This is not a mandatory staircase. Skip directly to exact evidence when the current claim genuinely requires it. If fidelity itself is unclear, read `references/resolution-ladder.md`; otherwise do not load that reference.

## 4. Check sufficiency after each useful retrieval

Stop when the material claims are covered and no unresolved issue is likely to change the answer.

Before `STOP`, check only what is relevant:

- material evidence covered?
- unresolved material conflict?
- freshness verified if required?
- exact evidence available if required?
- likely that one more bounded fetch changes the answer?

If insufficient, take **one narrow next action**. Re-enter from the current policy/action state; do not restart the whole routing process unless the task itself changed.

## 5. Bounded recovery and late specialization

An early entry choice is allowed to be wrong or incomplete.

If a selected specialized manifest clearly mismatches the task, or its specialist produces no useful next retrieval:

1. stop that branch;
2. try the retained backup candidate, if any;
3. otherwise fall back to GENERIC entry;
4. never recover by loading every remaining policy.

If GENERIC entry reveals a clear repository/document/research/state structure, specialize **then**, into one domain only.

A wrong first candidate is a recoverable routing event, not a fatal classification failure. A task with no clear specialist is also valid; specialization is optional.

## 6. Long-horizon context only when needed

Load retention guidance only for real multi-step/handoff pressure.

When active:

- `PIN` future-critical constraints, decisions, state, and evidence refs;
- `OFFLOAD` large recoverable outputs;
- `COMPACT` completed exploration at semantic boundaries;
- preserve a route back to raw source truth;
- count reacquisition when discarded context must be reconstructed.

## Invariants

- **Quality first.** Never trade verified task quality for token reduction.
- **Policy is context too.** ACE-S must progressively disclose its own rules.
- **Specialization is optional.** Do not force every ACTIVE task into a source domain.
- **One specialized candidate first.** At most one backup when specialization is chosen.
- **GENERIC is low-commitment, not catch-all expertise.** It has no specialist by default.
- **Lazy modifiers.** Do not classify/load every concern at task start.
- **Summaries are views, not truth.** Keep exact source recoverability when it matters.
- **Expand on insufficiency, not availability.** More accessible context is not a reason to load it.
- **Measure before claiming improvement.** Separate controller mechanics, taxonomy coverage, real-model routing, and end-to-end quality results.

Priority:

**correctness and completeness → recoverability/provenance → context efficiency → latency.**
