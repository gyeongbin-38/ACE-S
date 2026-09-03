# Selective Architecture Evidence Acquisition

Architecture quality can collapse when the designer either trusts stale intent documents or reads the entire system without a decision target. Gather evidence progressively around the decision that can change.

When ACE-S is available, use its context-policy kernel for retrieval. This reference defines **what architecture-changing evidence to request**, not a mandate to preload repository context.

## 1. Evidence classes

### Intent evidence
Use when the architecture question depends on promised behavior or accepted decisions:
- requirements / PRD / SRS
- ADRs / decision records
- architecture diagrams/design docs
- explicit constraints / compliance requirements
- ownership or operating agreements

Treat intent evidence as what the system is supposed to be, not automatically what it is.

### Observed implementation evidence
Use only as needed to test architecture claims:
- dependency/import/call edges
- public interfaces/contracts
- mutable state and storage access
- deploy/runtime topology
- configuration and feature flags
- authorization/enforcement points
- failure/retry/backpressure behavior
- tests around critical flows and boundaries
- selected change/co-change history

Treat observed implementation as evidence of current reality, not proof that current design is desirable.

## 2. Decision-targeted retrieval

Never ask "read the architecture" when a narrower question exists.

Translate architecture uncertainty into a retrieval target:

| Architecture question | First evidence target |
|---|---|
| Does this module own the invariant? | writes + validation/business-rule definitions around the state |
| Can these modules deploy independently? | deploy manifests + runtime config + cross-boundary contracts |
| Is this service split causing coordinated change? | selected boundary files + bounded co-change/history |
| Is this a trust boundary? | identity propagation + authorization enforcement + secret/resource access |
| Can this flow tolerate async consistency? | requirement/ASR + state transition rules + retry/idempotency behavior |
| Is this dependency a stable contract? | public interface/schema + callers + compatibility tests |
| Is the failure isolated? | call path + timeout/retry/backpressure + deployment/process boundary |

Start with the smallest artifact set that can falsify the current hypothesis.

## 3. Progressive evidence ladder

For repository-backed questions prefer:

1. known path/symbol/ADR/manifest;
2. exact lexical/symbol search;
3. local dependency neighborhood;
4. targeted call/data-flow slice;
5. bounded history/co-change for the candidate seam;
6. broad repository exploration only if the architecture question remains unresolved.

Do not compute global dependency/churn graphs merely because the tools exist.

## 4. Evidence packet

Return evidence to architecture synthesis as a small typed packet:

```text
architecture_question
hypothesis
facts[]
source_refs[]
observed_relations[]
contradictions[]
coverage_limit
confidence
next_disambiguating_check | null
```

Raw output should remain recoverable by source reference when possible.

## 5. Existing-system drift

When intent and implementation conflict, record:

```text
drift
  intended
  observed
  evidence_refs
  architecture_impact
  decision: preserve_intent | accept_reality | migrate | unresolved
```

Do not silently rewrite intent to match code or treat stale docs as current truth.

## 6. Change-history evidence

Change history is useful only when tied to a candidate boundary or volatility question.

Prefer bounded evidence such as:
- fraction of sampled changes touching both sides;
- repeated coordinated release/migration commits;
- files that frequently change with the boundary contract;
- whether changes localize after a prior boundary refactor.

Do not infer business volatility solely from git activity. History can be distorted by current architecture, refactors, generated files, or team workflow.

## 7. Stop rule

Stop retrieving when one of these is true:
- current architecture claim is falsified;
- current proof obligation is resolved;
- a hard constraint decides the option;
- remaining uncertainty is reversible and cannot change the current boundary;
- the next fetch is unlikely to change candidate elimination/Pareto position.

Retrieval should expand because of insufficiency, not because more repository context is available.
