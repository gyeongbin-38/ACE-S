# Evidence and Provenance Route

Use this route for high-stakes, disputed, exact, benchmark-sensitive, or externally sourced claims where the answer must remain auditable.

The objective is not merely to have sources. It is to preserve a **traceable chain from claim → evidence → source state**.

## 1. Classify evidence criticality

Use three fidelity classes:

- **EXACT** — contracts, policies, security rules, API fields, precise numbers, benchmark conditions, quotations, versioned requirements. Preserve verbatim or re-open raw evidence before use.
- **EXTRACTIVE** — a small exact region is sufficient; keep the relevant excerpt plus source location.
- **LOSSY** — orientation, completed exploration, and low-risk background can be summarized when the source remains recoverable.

Do not replace EXACT evidence with a summary merely to save context.

## 2. Build an evidence packet

For material claims, retain a compact packet:

```text
EvidencePacket
- claim: statement being supported
- source: stable source/entity/document/repository
- locator: URL, file/path, page, section, commit, record id, or timestamp
- source_state: version/date/revision when relevant
- evidence: concise extract or exact value
- fidelity: EXACT | EXTRACTIVE | LOSSY
- authority: primary | authoritative-secondary | secondary | community
- status: supports | contradicts | partial
- caveat: scope, definition, or uncertainty
```

The packet belongs in working context. Large raw material belongs behind a recoverable reference when possible.

## 3. Prefer direct evidence

Prefer evidence that is:

1. direct rather than quoted second-hand;
2. authoritative for the specific claim;
3. current enough for the requested time window;
4. scoped to the correct artifact, version, geography, or population;
5. independently corroborated when the claim is consequential or self-reported.

A source can be reputable and still be the wrong authority for a specific claim.

## 4. Resolve source conflicts

When two sources conflict, do not average them. Compare:

- ownership and authority,
- publication/update time,
- version or revision,
- measurement definition,
- scope/population,
- directness of the evidence,
- whether one source explicitly supersedes the other.

Choose a controlling source only when there is a principled reason. Otherwise preserve the conflict and lower confidence.

## 5. Preserve provenance through transformations

Summarization, extraction, aggregation, and handoff must not sever the path back to the source.

For every important transformed item, preserve at least one stable locator:

```text
summary → source_ref
aggregate → example/source refs
state field → originating record/commit
benchmark score → raw result rows + scoring formula
```

Treat summaries and aggregates as views, not the source of truth.

## 6. Re-open before finalizing exact claims

Re-check raw evidence immediately before using:

- exact field names or allowed values;
- policy/legal wording;
- numerical thresholds or dates;
- benchmark results and experimental conditions;
- quotations;
- changed requirements;
- disputed or surprising claims.

This protects against stale summaries and transcription drift.

## 7. Corroboration policy

Independent corroboration is most valuable when:

- the source has an incentive to overstate performance;
- the result is surprising or consequential;
- the claim depends on an interpretation rather than a direct fact;
- multiple measurement methods exist;
- the cost of being wrong is high.

Do not add redundant citations merely to increase source count.

## 8. Confidence and abstention

Confidence should reflect evidence quality, not writing fluency.

Use explicit uncertainty when:

- controlling evidence is unavailable;
- sources remain materially inconsistent;
- evidence is stale for a time-sensitive claim;
- the requested population/version is not represented;
- the conclusion depends on an unverified inference.

If missing evidence could reverse the answer, retrieve more or abstain from a definitive claim.

## 9. Final provenance check

Before answering or acting, verify:

- each material factual claim has adequate support;
- exact claims point to raw or extractive evidence;
- source state/version is current enough;
- contradictions are resolved or disclosed;
- transformed context retains a recoverable path to source truth.
