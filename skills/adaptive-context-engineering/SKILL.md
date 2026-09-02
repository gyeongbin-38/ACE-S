---
name: adaptive-context-engineering
description: Use this skill when a task may fail because context is missing, excessive, stale, conflicting, poorly scoped, or prematurely compressed. ACE-S first decides whether more context is needed, then loads only the smallest relevant policy manifest and specialist guidance, retrieves the narrowest useful context, and expands or switches policy only when evidence remains insufficient. Do not use for simple one-shot tasks already solvable from supplied context.
license: MIT
metadata:
  version: "0.3.0-alpha"
  methodology: "quality-first progressive policy loading"
  benchmark: "popular-repo-replay-v0.2 + routerbench-v0.1"
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

## 1. Coarse recognition

If `ACTIVE` or `UNCERTAIN`, identify only the **next likely context family**, not every possible route/modifier.

Ask at a coarse level:

- Does the next useful evidence primarily live in code/repository structure, a long document, external research, or conflicting/current state?
- Is there one materially plausible backup family if the first guess is wrong?

Then read `manifests/INDEX.md`.

Choose **one primary candidate**. Keep at most one backup when genuinely ambiguous. Do not score or classify every policy up front.

## 2. Progressive policy loading

Open only the selected candidate manifest. If it fits, open only the specialist reference named by that manifest.

Do **not** read all manifests or all specialist references “for awareness”.

Cross-cutting policies such as freshness, provenance, tool discovery, or retention are **lazy modifiers**. Load their manifest only when the current subproblem makes that concern material.

Example:

```text
repo task
  → CODE manifest
  → coding specialist
  → inspect repository
  → comparison now requires fresh external evidence
  → RESEARCH manifest
  → research specialist
  → freshness becomes material
  → TEMPORAL manifest
```

The architecture should emerge from the task as evidence is gathered; it should not be preloaded in full.

## 3. Retrieve the minimum useful context

Prefer the narrowest useful scope:

1. exact owner/path/symbol/entity/heading/source id;
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

## 5. Bounded recovery

An early coarse guess is allowed to be wrong.

If a selected manifest clearly mismatches the task, or its specialist produces no useful next retrieval:

1. stop that branch;
2. try the retained backup candidate, if any;
3. otherwise form one new candidate from what was learned;
4. never recover by loading every remaining policy.

A wrong first candidate is a recoverable routing event, not a fatal classification failure.

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
- **One candidate first.** At most one backup during coarse recognition.
- **Lazy modifiers.** Do not classify/load every concern at task start.
- **Summaries are views, not truth.** Keep exact source recoverability when it matters.
- **Expand on insufficiency, not availability.** More accessible context is not a reason to load it.
- **Measure before claiming improvement.** Separate controller-mechanics benchmarks from real-model routing and end-to-end quality results.

Priority:

**correctness and completeness → recoverability/provenance → context efficiency → latency.**
