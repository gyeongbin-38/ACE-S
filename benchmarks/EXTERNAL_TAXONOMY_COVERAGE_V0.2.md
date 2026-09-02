# External Taxonomy Coverage Stress v0.2

> **Controller:** frozen at `6e84f524aeb9bd761aa789445c1edb99cdadd9dd`.
>
> **No controller tuning was performed.**
>
> **Evidence level:** structural taxonomy stress; no model prediction is required for the headline result.

## Question

Does the frozen ACE-S primary-domain set:

`CODE / DOCUMENT / RESEARCH / STATE`

cover the kinds of context that appear in external agent tasks, or does it force unrelated work into an ill-fitting specialist?

## Dataset

v0.2 combines:

- the 24-case external holdout in [`unseen-routing-v0.1.json`](unseen-routing-v0.1.json);
- 16 additional tasks from the pinned SkillRouter Eval Core source.

The expansion intentionally adds tool/file/data-heavy tasks. It is a **stress distribution**, not a representative sample of all user conversations.

## Structural result

| Metric | v0.1 | v0.2 expanded |
|---|---:|---:|
| Total external tasks | 24 | **40** |
| DIRECT tasks | 9 | **9** |
| ACTIVE tasks | 15 | **31** |
| ACTIVE tasks cleanly covered by frozen primary domains | 9 | **11** |
| ACTIVE taxonomy gaps | 6 | **20** |
| Taxonomy coverage among ACTIVE | 60.0% | **35.5%** |
| Taxonomy gap rate among ACTIVE | 40.0% | **64.5%** |

### Gap families

| Gap | Count in v0.2 | Meaning |
|---|---:|---|
| `DATA_ARTIFACT` | **18** | operational context is primarily structured/binary/media/tabular data rather than repository structure, a long document, external research, or conflicting state |
| `WORKING_HISTORY` | **2** | context is primarily an agent/session/trajectory history that needs compaction/handoff rather than one of the four source domains |

## Examples driving DATA_ARTIFACT pressure

The external stress set includes tasks centered on:

- binary STL mesh data;
- PCAP network captures;
- Civ6 map data;
- stock CSV/history directories;
- video frames and masks;
- MSEED seismic traces;
- earthquake/plate JSON;
- ERP/CPI spreadsheets;
- MATPOWER network snapshots;
- gravitational-wave detector files;
- mixed invoice PDF + XLSX + CSV;
- receipt images;
- clinical CSV harmonization;
- climate/hydrology tables.

Forcing these into `CODE` merely because a script may process them conflicts with the frozen CODE manifest, whose trigger is **repository structure**. Forcing them into `DOCUMENT` also loses the difference between navigable prose hierarchy and operational data artifacts.

## Interpretation

### What this result supports

The frozen four-domain taxonomy is **too narrow for a general agent context controller** when the workload includes operational files/data.

### What it does not support

It does **not** prove that ACE-S fails 64.5% of real conversations. The expansion intentionally samples a tool-execution-heavy benchmark and therefore magnifies artifact-processing tasks.

It also does not prove that `DATA_ARTIFACT` should become a permanent fifth route.

## Better next hypothesis: avoid route explosion

Adding a new primary route every time an external task family appears would recreate the monolithic taxonomy problem.

The more conservative architecture candidate is:

```text
Tiny Kernel
   ↓
Is there a clearly dominant specialized source domain?
   ├─ YES
   │    → CODE / DOCUMENT / RESEARCH / STATE
   │    → one manifest
   │
   └─ NO
        → GENERIC / MODIFIER-FIRST entry
        → identify the minimum source/capability
        → TOOLS / RETENTION / EVIDENCE only when material
        → specialize later if evidence reveals a known domain
```

Under this design, `DATA_ARTIFACT` and `WORKING_HISTORY` remain **diagnostic categories**, not necessarily production primary routes.

This also changes the meaning of coarse recognition:

> The first question should not be “which one of four architectures is this?”
>
> It should be “does a specialist domain clearly dominate yet?”

That directly addresses the overfitting concern that motivated this redesign.

## Release implication

The current progressive-loading mechanism remains promising, but the **forced-primary-domain assumption should not be frozen as a public v0.4 contract yet**.

Before implementation changes:

1. keep the controller freeze intact;
2. expand with a more balanced external sample, including ordinary chat/rewrite/explanation tasks;
3. compare `forced primary` vs `generic/modifier-first fallback` mechanically;
4. then create a new candidate controller on a new branch;
5. evaluate the new candidate on another untouched external holdout.

Expansion fixture: [`external-taxonomy-expansion-v0.2.json`](external-taxonomy-expansion-v0.2.json)  
Scorer: [`../scripts/score_external_taxonomy_coverage.py`](../scripts/score_external_taxonomy_coverage.py)
