# ACE-S Examples

These examples show the **context decision**, not a model-specific prompt syntax. Exact tool calls vary by agent.

## 1. Direct answer — do nothing

**Task**

```text
What does `git rebase` do?
```

**ACE-S decision**

```text
route: DIRECT
retrieval: none
reason: current model context is sufficient for a general explanation
```

The skill is successful here by staying out of the way.

---

## 2. Repository bug — narrow structural expansion

**Task**

```text
A regression mentions `parseConfig`. Find the likely implementation and tests.
```

**Poor context strategy**

```text
repo root
→ read broad docs
→ global semantic search
→ many unrelated files
```

**ACE-S strategy**

```text
exact symbol: parseConfig
→ defining file
→ imported/called neighbors
→ sibling tests
→ sufficiency gate
```

**Working context**

```text
RepoEvidence
- symbol: parseConfig
- implementation: src/.../config.*
- callers: [...]
- tests: [...]
- unresolved: regression condition still unknown
```

---

## 3. Search miss — reduce query before broadening

**Task**

A long natural-language repository query returns no useful result, but the issue includes an exact function/type name.

**ACE-S strategy**

```text
long descriptive query failed
→ remove descriptive noise
→ exact symbol search
→ package/module neighborhood
→ broad semantic fallback only if needed
```

This pattern was useful in the public repository replay benchmark.

---

## 4. Long policy document — locator first, raw last

**Task**

```text
Find the exception that permits an otherwise ineligible contractor to apply.
```

**ACE-S strategy**

```text
TOC / heading map
→ search "contractor" / likely eligibility heading
→ inspect candidate section
→ include surrounding qualifiers
→ open raw exact wording
→ cite page/section
```

**Do not** summarize the entire policy before locating the controlling clause.

---

## 5. Current vs historical state

**Input**

```text
January note: timeout = 30
July change: timeout = 60
```

**Task**

```text
What is the timeout now, and what changed?
```

**ACE-S working state**

```text
current:
  timeout: 60
history:
  - value: 30
    status: superseded
```

Old and new values should not be merged into an ambiguous summary such as "timeout is 30–60".

---

## 6. Research comparison — claim ledger

**Task**

```text
Compare library A and B for a production deployment.
```

**ACE-S working context**

```text
Claim: A supports required runtime
  status: supported
  source: primary docs

Claim: B has lower measured latency
  status: mixed
  source: benchmark + independent report
  caveat: different hardware

Claim: A fits deployment constraint X
  status: supported
```

The final recommendation is generated from the claims and constraints, not browsing chronology.

---

## 7. Multi-step workflow — compact at a decision boundary

**Workflow**

```text
research candidates → choose one → implementation plan → code
```

After the choice is made, compact the exploration into:

```text
HandoffState
- objective
- selected candidate/version
- binding constraints
- decision + rationale
- evidence refs
- implementation risks
- next action
```

Discard or offload repeated searches and rejected-candidate chatter unless a rejection reason will matter later.

---

## 8. Evidence-critical API field

**Task**

```text
Tell me the exact allowed values for `mode` before I write the integration.
```

**ACE-S strategy**

```text
summary may locate the contract
→ authoritative raw API/schema
→ exact field name and enum values
→ final answer
```

A lossy summary must not substitute for the exact contract.

---

## 9. Large tool output

**Input**

```text
20,000 log lines
```

**ACE-S strategy**

```text
index/error signatures
→ relevant time/error windows
→ exact surrounding lines
→ compact diagnosis + raw log reference
```

The full log remains recoverable but does not stay in the working prompt.

---

## Reusable decision shape

A runtime implementing ACE-S can represent each context decision with a shape like:

```text
ContextDecision
- route
- target
- resolution
- evidence_needed
- current_sufficiency
- next_expansion
- stop_reason
```

This is an illustrative interface, not yet a stable protocol. A typed controller schema is on the roadmap.
