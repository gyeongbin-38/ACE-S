---
name: adaptive-context-engineering
description: Use this skill when a task may suffer from too much, too little, stale, conflicting, or poorly scoped context: long or multi-step work, deep research, many files or tools, repository investigation, long documents, conflicting historical facts, handoffs, or explicit context/token optimization. It selects the smallest sufficient evidence set and expands only when needed. Do not use for simple one-shot questions, casual conversation, creative writing, or tasks already solvable from the current context without additional retrieval.
license: MIT
metadata:
  version: "0.1.0-alpha"
  methodology: "quality-first adaptive context selection"
---

# Adaptive Context Engineering

Optimize **successful-task quality per unit of context**, not token count in isolation.

## 1. Activation gate

Before retrieving or loading more material, ask:

1. Is the current context already sufficient to answer reliably?
2. Would additional retrieval materially reduce uncertainty or prevent an important error?

If both answers are no, solve directly. **No retrieval is a valid action.**

## 2. Classify the context problem

Choose one primary route:

- **Direct** — current/recent context is sufficient.
- **Research** — multiple external sources or synthesis are required.
- **Long document** — information is inside one or more large documents.
- **Code / repository** — symbols, files, dependencies, tests, or change impact matter.
- **Temporal / conflicting state** — facts may have changed, been superseded, or conflict.
- **Plan-aware** — later workflow steps will need information gathered now.
- **High-risk evidence** — exact wording, provenance, independent corroboration, or verification matters.

If classification is uncertain, use the generic Resolution Ladder rather than guessing a specialist route.

## 3. Start with the smallest useful scope

Prefer, in order when applicable:

1. exact owner/path/symbol/entity/index
2. lexical or structured lookup
3. local dependency / hierarchy neighborhood
4. task-aware or semantic retrieval
5. broad search only as fallback

Do not load every available file, tool, skill, source, or conversation segment by default.

## 4. Use the Resolution Ladder

Read information at the lowest fidelity that can safely answer the current question:

1. **Index / metadata**
2. **Compact summary**
3. **Relevant extract**
4. **Raw exact evidence**

Escalate one level only when the current level is insufficient.

Use raw evidence immediately for exact contracts, quotations, precise numbers, changed requirements, disputed facts, or other fidelity-critical material.

See `references/resolution-ladder.md` when a task has large documents, large tool output, or long histories.

## 5. Apply the specialist route only when needed

- Code/repository tasks → read `references/coding.md`.
- Conflicting, changing, or historical state → read `references/temporal.md`.
- Deep research or multi-source synthesis → read `references/research.md`.
- Multi-step workflows → read `references/plan-aware.md`.
- High-risk claims or source disputes → read `references/evidence-and-provenance.md`.

Do not load unrelated reference files.

## 6. Sufficiency gate

After each retrieval round, check:

- Do I have the evidence needed for every material claim or action?
- Are important contradictions unresolved?
- Is any missing evidence likely to change the answer?
- Can I trace high-risk claims back to a source or exact record?

If sufficient, stop retrieving. If not, expand the narrowest relevant scope or raise the resolution level.

## 7. Context hygiene during long work

- Keep current goals, constraints, decisions, unresolved questions, and evidence references separate from raw history.
- Treat summaries as **views, not source of truth**.
- Preserve a route back to raw evidence for important decisions.
- At semantic task boundaries, compact completed exploration into concise state plus references.
- Keep large tool outputs or logs out of the main working context when they can be re-read by reference.

## 8. Final verification

Before answering or acting:

1. Re-check fidelity-critical facts against raw evidence.
2. Confirm the final answer uses the current, not superseded, state.
3. Make uncertainty explicit where evidence remains incomplete.
4. Do not claim an optimization improved quality unless it was measured against a baseline.

The default priority is:

**correctness and completeness → recoverability/provenance → context efficiency → latency.**
