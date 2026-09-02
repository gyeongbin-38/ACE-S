# ACE-S Unseen Routing + Recovery v0.1

> **Controller:** frozen at `6e84f524aeb9bd761aa789445c1edb99cdadd9dd` before holdout construction.
>
> **Prompt origin:** third-party public benchmark tasks, pinned by upstream commit.
>
> **Prediction evidence:** single GPT-5.6 Sol conversational sanity pass. **Not blind**: the same assistant session mapped ACE-S gold labels and produced predictions. Do not use the model rates below as a stable routing-performance claim.

## Why this experiment is different

The earlier RouterBench prompts and signal-aware controller prototype were created in the same experiment cycle, which created a clear overfitting/leakage risk.

For this test:

1. the progressive controller was frozen first;
2. a new evaluation branch was cut from that SHA;
3. task wording was selected from two external public benchmarks;
4. controller policy files were not edited;
5. missing taxonomy coverage was recorded as a failure of representation rather than patched against the holdout.

## Fixture composition

| Item | Count |
|---|---:|
| Total external tasks | 24 |
| DIRECT | 9 |
| ACTIVE | 15 |
| ACTIVE covered by frozen four-domain taxonomy | **9** |
| ACTIVE with no clean frozen primary domain | **6** |

### Structural taxonomy result

```text
Frozen primary domains:
CODE / DOCUMENT / RESEARCH / STATE

External ACTIVE tasks cleanly covered: 9 / 15 = 60.0%
External ACTIVE taxonomy gaps:         6 / 15 = 40.0%
```

This is the most important result in v0.1.

The model can potentially notice that a chosen manifest does not fit, but **bounded recovery cannot recover into a policy that does not exist**. A 40% gap rate on this small external sample means the current domain taxonomy is not yet broad enough to freeze as a stable public controller API.

## Gap families found

| Gap family | Count | What the task context actually is |
|---|---:|---|
| `WORKING_HISTORY` | 2 | conversation/trajectory/session history that needs compaction or handoff |
| `DATA_ARTIFACT` | 4 | binary/structured operational artifacts such as STL, topology JSON, Civ6 map data, or PCAP |

These labels are diagnostic only. They are **not** new production routes yet.

## Single-run GPT-5.6 Sol sanity pass

| Metric | Result |
|---|---:|
| Activation accuracy | 100.0% |
| DIRECT with no policy load | 100.0% |
| Primary top-1 accuracy on taxonomy-covered ACTIVE tasks | 100.0% |
| Primary-or-backup coverage on taxonomy-covered ACTIVE tasks | 100.0% |
| Gap detection after manifest mismatch | 100.0% |
| Candidate budget compliance | 100.0% |
| Route-or-gap resolution | 100.0% |

### Do **not** read this table as “ACE-S scores 100%”

The single-run predictions are useful only as a smoke test because the evaluator was not independent. More importantly, the model-level table is conditional on acknowledging six taxonomy gaps.

A model saying “this manifest does not fit; the taxonomy is missing DATA_ARTIFACT” is **not** the same as ACE-S successfully routing the task.

Therefore the defensible headline from this run is:

> **The frozen controller remained selective on a small external sanity set and could reject mismatched manifests, but only 60% of ACTIVE external tasks had a clean primary domain in the frozen taxonomy.**

## What failed structurally

### 1. Primary-domain routing is still too source-type-specific

The four domains work well for:

- repository structure;
- bounded long documents;
- external multi-source research;
- current/superseded/conflicting state.

They do not cleanly cover a large class of tool-agent work where context is simply an **operational artifact**:

- a packet capture;
- a binary mesh;
- structured JSON topology;
- map/database-like task data.

Forcing these into `CODE` because a script might process the file violates the CODE manifest, which explicitly requires repository structure to dominate.

### 2. Long-running history does not naturally need a primary source domain

Conversation/trajectory compaction and handoff are already handled conceptually by `RETENTION`, but the frozen kernel still asks for a primary context family first.

That creates an unnecessary forced choice such as `DOCUMENT` for a chat history even when no supplied document is involved.

This suggests the architecture may need a **modifier-only / generic-context entry path**, rather than simply adding more and more primary domains.

## Design implication — do not immediately add two more routes

The naive reaction would be:

```text
+ DATA_ARTIFACT domain
+ WORKING_HISTORY domain
```

That risks restarting the same taxonomy explosion that progressive loading was meant to prevent.

A more conservative next hypothesis is:

```text
Tiny Kernel
   ↓
Does one specialized source domain clearly dominate?
   ├─ yes → load CODE / DOCUMENT / RESEARCH / STATE manifest
   └─ no  → GENERIC / MODIFIER-FIRST context path
               ↓
          TOOLS / RETENTION / EVIDENCE as needed
```

This would let operational artifacts and working history avoid pretending to be repository/document/research/state tasks while keeping the number of specialist domains small.

**This hypothesis is not implemented on the v0.1 holdout branch.** It must be tested against a larger external sample first.

## Comparison with previous experiments

| Experiment | Main question | Key result | Evidence limitation |
|---|---|---|---|
| Authored RouterBench | Can layered labels fit authored routing cases? | 92.9 / 97.8 prototype scores | policy + stress cases co-developed; leakage risk |
| Selective Policy Load Bench | Can progressive loading reduce policy load mechanically? | Progressive + Recovery 98.6 mechanics score; 51.6% fewer policy bytes than full-load | oracle task requirements; no natural-language routing |
| **External Unseen v0.1** | Does the frozen taxonomy cover external task wording/types? | **60% structural ACTIVE-domain coverage; 40% gaps** | small sample; gold mapping not independently annotated |

The experiments now answer different questions instead of collapsing into one misleading headline score.

## Next experiment

Before changing the taxonomy:

1. expand the external holdout to at least 75–100 tasks;
2. keep the current controller SHA frozen;
3. measure how often `DATA_ARTIFACT`, `WORKING_HISTORY`, or other unmapped families recur;
4. separately measure whether a `GENERIC / MODIFIER-FIRST` fallback would resolve those cases without increasing policy load;
5. only then create a new controller candidate and compare it against the frozen one on a fresh holdout.

Fixture: [`unseen-routing-v0.1.json`](unseen-routing-v0.1.json)  
Protocol: [`UNSEEN_ROUTING_PROTOCOL.md`](UNSEEN_ROUTING_PROTOCOL.md)  
Scorer: [`../scripts/score_unseen_routing.py`](../scripts/score_unseen_routing.py)  
Raw sanity predictions: [`results/unseen-routing-v0.1-gpt-5.6-sol-single-run.json`](results/unseen-routing-v0.1-gpt-5.6-sol-single-run.json)
