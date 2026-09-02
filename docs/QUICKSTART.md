# ACE-S Quickstart

ACE-S is not another memory database or agent framework. It is a **context-selection policy** that tells an agent what to inspect, at what fidelity, and when to stop.

## Install

```bash
npx skills add gyeongbin-38/ACE-S \
  --skill adaptive-context-engineering
```

If your agent supports repository-local skills, keep the installed skill available by default and let the activation gate decide whether it should intervene.

## The 30-second mental model

```text
Do I already have enough context?
  ├─ yes → solve directly
  └─ no  → classify the context problem
              ↓
          choose one route
              ↓
        load the smallest useful scope
              ↓
      index → summary → extract → raw
              ↓
          sufficiency check
          ├─ enough → stop
          └─ missing → expand one narrow step
```

ACE-S does **not** reward retrieval for its own sake. `DIRECT` is a successful route when the current context is already sufficient.

## Example 1 — repository work

Prompt:

```text
Find the cause of the parseConfig regression and tell me which files need editing.
```

Expected ACE-S behavior:

```text
1. Locate parseConfig exactly.
2. Inspect its defining file.
3. Inspect direct callers/dependencies and relevant tests.
4. Stop if that local neighborhood explains the regression.
5. Broaden only if the local evidence is insufficient.
```

Avoid:

```text
read every README
→ semantic-search the whole repo
→ load unrelated files
→ summarize everything
```

## Example 2 — deep research

Prompt:

```text
Compare approach A and B for production use and recommend one.
```

Expected behavior:

```text
Decision frame
→ capability claims
→ measured performance
→ operational constraints
→ primary sources
→ only necessary corroboration
→ claim ledger
→ sufficiency stop
```

The final answer should separate source-backed evidence from inference and recommendation.

## Example 3 — long document

Prompt:

```text
In this 120-page policy, find the exact exception that applies to contractors.
```

Expected behavior:

```text
TOC / headings / exact term
→ candidate section
→ contiguous surrounding section
→ raw wording for the exception
→ page/section reference
```

Do not summarize all 120 pages first.

## Example 4 — long workflow

Prompt:

```text
Research three libraries, choose one, then prepare an implementation plan.
```

ACE-S should retain:

```text
- still-binding constraints
- decision and concise rationale
- evidence references
- selected library/version
- unresolved implementation risks
```

It should compact:

```text
- rejected-search chatter
- duplicated tool output
- already-resolved exploratory branches
```

## Example 5 — no retrieval

Prompt:

```text
Explain why Python lists are mutable in two sentences.
```

If the agent already knows enough to answer reliably, ACE-S should stay dormant and answer directly.

## How to tell whether ACE-S is working

Good behavior looks like:

- fewer irrelevant files/sources opened;
- exact contracts are still checked raw;
- broad search happens later, not first;
- current state is not merged with superseded state;
- long tool output is reduced to evidence + recoverable refs;
- the agent stops retrieving once additional context is unlikely to change the answer.

Bad behavior looks like:

- always retrieving because the skill exists;
- using summaries where exact evidence is required;
- carrying full search transcripts into downstream prompts;
- treating vector similarity as sufficient for structural code tasks;
- compacting away constraints that later steps still need.

## Route map

| Problem | Specialist reference |
|---|---|
| Code/repository | `references/coding.md` |
| Long PDF/spec/document | `references/long-document.md` |
| Current vs historical/conflicting state | `references/temporal.md` |
| Multi-source research | `references/research.md` |
| Multi-step workflow/handoff | `references/plan-aware.md` |
| Exact/high-risk/provenance-sensitive claims | `references/evidence-and-provenance.md` |
| Mixed/uncertain problem | `references/resolution-ladder.md` |

## Next step

Read [`../skills/adaptive-context-engineering/SKILL.md`](../skills/adaptive-context-engineering/SKILL.md) for the compact controller, or open the [Archify architecture](archify/ace-s.architecture.html) for the full map.
