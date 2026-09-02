# Research Route

Use this route when a task requires current information, multiple sources, comparison, synthesis, or a recommendation grounded in external evidence.

The objective is **decision-relevant evidence coverage**, not maximum browsing volume.

## 1. Frame the research decision

Before searching, write the smallest useful research frame:

```text
ResearchFrame
- question: what must be answered?
- decision: what choice or conclusion will this support?
- constraints: date, geography, population, version, budget, scope
- claims_needed: facts that must be established
- freshness: evergreen | current | breaking
```

Broad search without a decision frame tends to accumulate interesting but irrelevant context.

## 2. Decompose into claims

Break the task into material claims or unknowns. Search to resolve those claims rather than following browsing order.

Example:

```text
"Which approach should we adopt?"
→ capability
→ measured performance
→ operational cost
→ limitations
→ compatibility with our constraints
```

Keep evidence grouped by claim.

## 3. Use a source hierarchy

Prefer the most direct source that can establish each claim:

1. primary specification, paper, repository, official announcement, dataset, filing, or documentation;
2. authoritative independent analysis;
3. reputable reporting or secondary synthesis;
4. community discussion for experience, sentiment, or failure reports;
5. low-authority summaries only for discovery, not as the sole support for important claims.

Do not require multiple sources when one primary source directly resolves a low-risk fact. Seek independent corroboration when the claim is consequential, disputed, surprising, or vulnerable to self-reporting bias.

## 4. Search progressively

Use the smallest query that can resolve the current claim:

1. exact entity / paper / repository / field / error / metric;
2. authoritative-domain search;
3. targeted comparison or failure-mode search;
4. semantic or broader discovery search;
5. broad landscape search only when the candidate set itself is unknown.

If a long descriptive query fails, remove explanatory noise and retry with exact entities or terms before broadening.

## 5. Maintain a claim ledger

For non-trivial research, retain a compact ledger:

```text
Claim
- statement
- status: supported | mixed | unsupported | stale
- best_source
- corroboration
- freshness
- scope
- caveat
```

The ledger is the working context. Search transcripts are not.

## 6. Resolve contradictions explicitly

When sources disagree, do not average them. Compare:

- publication/update time,
- primary vs secondary ownership,
- measurement definition,
- population/sample/version,
- experimental conditions,
- whether one source supersedes another.

If the conflict matters and cannot be resolved, preserve it in the final answer instead of collapsing it into false certainty.

## 7. Freshness policy

For changing topics, verify that at least one controlling source matches the requested time window.

Treat versioned software, prices, policies, model releases, benchmarks, schedules, and organizational claims as potentially stale unless a date/version is established.

Do not merge old and new states into one timeless summary.

## 8. Sufficiency gate

Stop researching when:

- every decision-relevant claim is supported or explicitly marked uncertain;
- remaining gaps are unlikely to change the recommendation;
- major contradictions are resolved or disclosed;
- additional sources would mostly duplicate existing evidence.

Continue only if the next search has a plausible path to changing the answer.

## 9. Final synthesis

Build the final answer from the claim ledger, not from browsing chronology.

For recommendations, distinguish:

- **evidence** — what sources establish;
- **inference** — what follows from combining evidence;
- **judgment** — the recommendation under the stated constraints.

Re-open raw primary evidence for exact numbers, quotations, benchmark conditions, or disputed claims before finalizing.
