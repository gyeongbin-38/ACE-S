# Generic Candidate — Fresh External Holdout v0.1

> **Candidate policy frozen before prompt inspection:** `0e9a0ba03bfda7ffb8997a68f63e46dfcdbad503`
>
> **External source:** SkillRouter Eval Core, pinned commit `21f4bc31327a4d2beebfb454c159860ea21d8631`, task lines 51–75.
>
> **Evidence level:** fresh structural/architecture holdout. No independent model-routing claim is made here.

## Why this holdout matters

The previous external stress exposed a major weakness in the forced-primary controller: operational data/artifact tasks and working-history tasks did not naturally fit `CODE / DOCUMENT / RESEARCH / STATE`.

A new candidate introduced an optional **Specialization Gate**:

```text
ACTIVE
  ↓
Does a specialist clearly dominate the next context step?
  ├─ YES → SPECIALIZED → one domain
  └─ NO  → GENERIC → no specialist by default
```

The candidate was frozen **before** opening this source range. The evaluation branch has a CI guard that rejects edits to frozen policy files.

## Holdout composition

25 external tasks were manually mapped after the freeze.

To avoid manufacturing exact labels for genuine boundary cases, cases are split by label strength:

| Gold strength | Count | Treatment |
|---|---:|---|
| Hard SPECIALIZED | **9** | one specialist source domain clearly dominates |
| Hard GENERIC | **9** | no frozen specialist source domain clearly dominates |
| Ambiguous | **7** | both GENERIC and one named specialist are considered acceptable |

The hard subset is deliberately balanced 9:9, so a controller cannot look good by always choosing GENERIC or always choosing SPECIALIZED.

Examples of hard SPECIALIZED tasks include repository code translation, React performance debugging, Python-library fuzzing setup, paper-to-repository code reproduction, and Spring migration.

Examples of hard GENERIC tasks include PDDL problem artifacts, video counting, spreadsheet transformation, slide editing, seismic waveform arrays, diarization media, and PCAP/rule workflows.

## Structural comparison on the 18 hard cases

| Metric | Frozen forced-primary controller | **Optional-specialization candidate** |
|---|---:|---:|
| Hard representational fit | **50.0%** | **100.0%** |
| Hard specialist-task preservation | **100.0%** | **100.0%** |
| Hard GENERIC entry coverage | **0.0%** | **100.0%** |
| Unnecessary specialist load on hard GENERIC tasks | **100.0%** | **0.0%** |
| Mean entry policy bytes | **9,966.1*** | 11,928.1 |

\* The forced-primary byte figure is intentionally optimistic: every hard GENERIC task is charged the **cheapest** available old specialist entry (`STATE`, 9,139 bytes), regardless of semantic mismatch. It is therefore a lower bound on forced-primary entry cost, not a realistic router prediction.

## The important trade-off

Optional specialization fixes the **representation** problem, but its current entry policy is not smaller than the old forced-primary path.

```text
Old optimistic mean entry policy:  9,966.1 bytes
New oracle mean entry policy:      11,928.1 bytes
Difference:                        +1,962.0 bytes (~+19.7%)
```

The new architecture buys broader representational coverage and eliminates unnecessary specialist loading on the hard GENERIC subset, but currently pays for a larger kernel/index plus the GENERIC manifest.

Therefore the defensible result is **not** “GENERIC saves tokens”. It is:

> **Optional specialization removes a structural forced-routing failure on this fresh balanced holdout, while increasing the initial policy-byte cost in the current implementation.**

Whether the larger entry cost is recovered by avoiding wrong specialist reads, extra retrieval, and downstream reacquisition must be measured end-to-end.

## Why the 7 ambiguous cases are not forced into the score

The holdout includes real mixed boundaries such as:

- old PDF vs current spreadsheet comparison — GENERIC or STATE;
- fetching specific web essays then TTS — GENERIC or RESEARCH;
- numerical simulation with paper references — GENERIC or RESEARCH;
- current external financial data plus spreadsheet work — GENERIC or RESEARCH;
- calendar/email scheduling — GENERIC or STATE;
- historical quarter datasets — GENERIC or STATE;
- dependency audit with vulnerability evidence — GENERIC or RESEARCH.

Forcing one exact route in these cases would reward our own annotation preference rather than controller quality. They should instead be used in a real-model evaluation with acceptable-mode sets and downstream success checks.

## New failure risk: GENERIC overuse

The candidate solves forced specialization by creating a low-commitment path, but that introduces the opposite risk:

```text
clear CODE/RESEARCH/etc. task
   ↓
model chooses GENERIC because it is safer
   ↓
extra inspection / delayed specialization
   ↓
latency and context overhead
```

The fresh holdout contains nine hard specialist tasks specifically to detect this. A future model sweep must report:

- specialization decision accuracy;
- GENERIC overuse rate on hard specialist tasks;
- forced-specialization rate on hard generic tasks;
- domain accuracy conditional on SPECIALIZED;
- late-specialization rate and cost;
- policy bytes/tokens and downstream retrieval rounds.

## Current conclusion

The candidate passes the **architecture representation gate**, not the model-routing gate.

It is a better representational interface than forced-primary routing on this fresh holdout because it can express both strong specialist and non-specialist tasks without inventing new permanent domains.

However, the current kernel/index/generic entry is approximately 19.7% more expensive at the initial policy layer than an optimistic forced-primary lower bound. That overhead must be attacked **only on a new development cycle**, not by tuning the frozen candidate against this holdout.

## Next gate

1. keep this holdout sealed;
2. do not edit the frozen candidate on the evaluation branch;
3. run an independent model/provider on the 25 external task IDs when such a provider is available;
4. measure SPECIALIZED-vs-GENERIC decisions and downstream late specialization;
5. create any kernel/index compaction candidate on a new branch;
6. evaluate that candidate on another untouched task range.

Fixture: [`generic-candidate-unseen-v0.1.json`](generic-candidate-unseen-v0.1.json)  
Scorer: [`../scripts/score_generic_candidate_holdout.py`](../scripts/score_generic_candidate_holdout.py)  
Freeze: [`FROZEN_GENERIC_CANDIDATE_V04.json`](FROZEN_GENERIC_CANDIDATE_V04.json)
