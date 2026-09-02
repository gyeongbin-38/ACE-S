# Long-Document Route

Use this route when the answer is buried inside a large PDF, specification, policy, report, book, transcript, or multi-file document set.

The goal is not to read everything. The goal is to reach the **smallest contiguous evidence region that can answer the task without losing document structure or exactness**.

## 1. Establish the document map

Start with the cheapest reliable structure available:

1. title / metadata / document version,
2. table of contents or headings,
3. page or section index,
4. exact-term or heading search,
5. semantic search only when structure and lexical search are insufficient.

Do not summarize the whole document before locating the relevant region.

## 2. Resolve the target region

Convert the user's request into likely anchors:

- exact names, terms, IDs, clauses, symbols, dates, or entities;
- likely headings or neighboring concepts;
- expected evidence type: definition, exception, procedure, number, table, quotation, or conclusion.

Use those anchors to identify one or a few candidate regions.

## 3. Read contiguous context, not disconnected snippets

A search hit is a locator, not necessarily sufficient evidence.

Once a candidate hit is found:

- open the surrounding paragraph/section/page range;
- include definitions or qualifiers immediately above it when they control interpretation;
- follow cross-references only when they materially affect the answer;
- preserve page/section coordinates for later verification.

For a chapter or section summary, identify its boundaries and read the full section rather than stitching unrelated search snippets together.

## 4. Escalate fidelity deliberately

Use the Resolution Ladder:

`metadata/index → section summary → relevant extract → raw exact text/table`

Jump directly to raw evidence when the task asks for:

- exact wording,
- eligibility or legal/policy exceptions,
- numerical thresholds,
- tables or formulas,
- changed requirements,
- citations or quotations,
- disputed interpretation.

## 5. Handle scanned or visual pages

If parsed text is missing, garbled, or structurally misleading, inspect the page image rather than repeatedly searching broken text.

Visual inspection is especially important for:

- tables,
- diagrams,
- multi-column layouts,
- footnotes,
- scanned pages,
- formatting-dependent exceptions.

## 6. Sufficiency gate

Stop expanding when all of the following are true:

- the requested claim/action is supported by a contiguous source region;
- controlling qualifiers and exceptions have been checked;
- exact facts are traceable to page/section coordinates;
- no unresolved cross-reference is likely to change the conclusion.

Expand only the narrowest missing dimension: neighboring section, referenced clause, exact table, or another document version.

## 7. Compact for downstream work

Keep a small document evidence packet instead of the full reading trail:

```text
DocumentEvidence
- document: stable title / version / id
- target: question or claim
- location: page / section / heading
- finding: concise interpretation
- exactness: summary | extract | raw
- source_ref: recoverable pointer to original region
- unresolved: remaining ambiguity or cross-reference
```

Treat the packet as a working view. The original document remains the source of truth.
