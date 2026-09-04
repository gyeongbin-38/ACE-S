# Architecture Memory Milestone — 2026-09-04

Status: `INTERMEDIATE_MILESTONE_BEFORE_INTERACTIVE_SUITE_C1`

Branch: `exp/architecture-memory-runtime-v01`

This document records the architecture-memory research progress after the frozen v0.1 candidate, fresh deterministic OOD, and the first blind Luna replay. It does not modify the frozen candidate or retrospectively tune any held-out benchmark.

## 1. What changed

The architecture-memory work moved from **selective context retrieval** toward **transactional canonical-state management**.

Earlier ACE-S behavior mainly optimized which policies and context fragments entered the worker context. That reduced irrelevant context, but relevance alone did not answer a harder question:

> When history contains current, superseded, speculative, aborted, and reopened states at the same time, which state is allowed to control execution now?

The v0.1 research candidate answers that by separating five roles:

```text
Append-only Event Log
        |
        v
Transactional State Tree
        |
        v
Typed Canonical Architecture Graph
        |
        +--> Hard-Constraint + Proof-Obligation Ledger
        |
        v
Bounded Worker Projection
```

The central invariant is now:

```text
MODEL_PROPOSAL != CANONICAL_STATE
```

and the associated execution distinction is:

```text
history != current truth != speculative state != obligations != worker view
```

### Practical consequences

- Speculative model proposals no longer mutate canonical state before validation.
- Nested branch changes can be committed locally and still disappear from active truth if an enclosing branch is later aborted.
- Superseded decisions remain auditable history without remaining active.
- Hard constraints and unresolved proof obligations are pinned state, not ordinary semantic memories.
- Every active architecture fact must retain provenance.
- Worker context is generated as a bounded view over canonical state rather than being treated as the source of truth.

## 2. Fresh deterministic OOD evidence

Frozen runner commit: `c73feb48d0299a1acdf27e99de28e351272eb947`

Candidate freeze commit: `78a4f9072ee91833eedf50d30a4f772969ad9ce7`

Result artifact:

`benchmarks/runtime-traces/results/architecture-memory-runtime-ood-v0.1-result.json`

The benchmark used six failure families and 58,273 queries per strategy:

- nested abort after inner commit;
- nested commit after inner abort;
- supersession after long gap;
- obligation reopen cycle;
- owner reassignment;
- compound recovery.

### Result summary

| Strategy | Current state | Hard constraints | Obligations | Provenance | Aborted contamination | Mean worker-visible facts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sliding window stress baseline | 0.000% | 0.000% | 0.000% | 0.000% | 0.000% | 72.00 |
| Semantic event RAG | 87.097% | 87.290% | 86.970% | 87.136% | 12.893% | 5.00 |
| Hierarchical state tree | 100.000% | 100.000% | 100.000% | 0.000%* | 0.000% | 34.00 |
| Mutable typed graph | 87.097% | 87.290% | 86.970% | 87.136% | 12.893% | 4.00 |
| **Transactional typed hybrid** | **100.000%** | **100.000%** | **100.000%** | **100.000%** | **0.000%** | **3.47** |

`*` The hierarchical-tree provenance result is specific to this synthetic baseline, which intentionally drops exact raw provenance beyond its compression horizon. It is not a general claim that hierarchical memory cannot preserve provenance.

The frozen quality gate passed all conditions.

### What this established

The deterministic controller evidence supports the architectural claim that transaction isolation is necessary when speculative state and canonical truth coexist. A typed graph alone did not solve branch validity; semantic retrieval alone did not solve active-vs-aborted truth; the transactional hybrid did.

This evidence is controller-mechanics evidence only. It does not by itself establish improved LLM memory.

## 3. Blind Luna replay evidence

Result artifact:

`benchmarks/runtime-traces/results/luna-archret-v01b-result.json`

The hidden condition mapping was opened only after all three outputs had been received. The resulting mapping was:

- `K0` = `TRANSACTIONAL_TYPED_HYBRID`
- `K1` = `CURRENT_ACE_PROGRESSIVE`
- `K2` = `OFF_FULL_HISTORY`

### Aggregate result

| Metric | OFF / full history | Current ACE progressive | **Transactional hybrid** |
| --- | ---: | ---: | ---: |
| Exact task success | 15/18 (83.333%) | 13/18 (72.222%) | **17/18 (94.444%)** |
| Component exact | 195/198 (98.485%) | 188/198 (94.949%) | **197/198 (99.495%)** |
| Current-state value accuracy | 100.000% | 95.556% | **100.000%** |
| Provenance accuracy | 100.000% | 95.556% | **100.000%** |
| Hard-constraint retention | 100.000% | 97.143% | **100.000%** |
| Obligation-value retention | 100.000% | 84.211% | **100.000%** |
| Gate accuracy | 83.333% | 88.889% | **94.444%** |
| Missing fact-value errors | 0 | 4 | **0** |
| Aborted-branch contamination | 0 | 0 | **0** |

Against current ACE progressive, the transactional hybrid produced:

- `+22.222 pp` exact task success;
- `80%` failed-task-count reduction;
- `+4.546 pp` component score;
- `90%` component-error-count reduction;
- `+15.789 pp` obligation-value retention;
- `+5.555 pp` gate accuracy.

Against OFF/full history, it produced:

- `+11.111 pp` exact task success;
- `66.667%` failed-task-count reduction;
- `+1.010 pp` component score;
- `66.667%` component-error-count reduction;
- `+11.111 pp` gate accuracy.

### Important interpretation

This is the first real-model evidence in this research line, but it is still a **memory-view replay**. The hybrid condition receives a controller-generated canonical projection. Therefore the supported claim is:

> Given the transactional runtime's canonical worker view, Luna answered active-state, provenance, obligation, and execution-gate questions more reliably than the two baselines in this blind replay.

The unsupported stronger claim is:

> Luna intrinsically forgets less over arbitrary long-running agent sessions.

That stronger claim remains gated on the interactive Suite C1 experiment.

## 4. Harness calibration progress

A separate Suite C0 calibration was executed externally through Paseo with GPT-5.6 Luna at xhigh reasoning.

Reported execution properties:

- three opaque conditions completed;
- 8/8 sequential stages per condition;
- 6/6 final tasks per condition;
- zero malformed outputs;
- zero transport retries;
- fresh session isolation across conditions;
- web disabled;
- labels and condition mapping left unopened.

This is **harness validation only** and must never be counted as held-out performance evidence. The raw C0 outputs are not yet represented in this repository by independently hashed receipts, so this milestone records the execution report but does not promote it to benchmark evidence.

## 5. Methodological progress

The research process itself improved in several ways.

### Benchmark labels are now treated as evidence

A previous Kubernetes replay task exposed a wrong gold label: the benchmark pointed to `loader.go` while the actual current-context persistence owner in the frozen source was `config.go`. The lesson is now explicit: benchmark quality and gold-label provenance are first-class parts of the experiment, not administrative details.

### Freeze before evaluation

The architecture candidate, runner, blind mapping, packet representation, and result chronology are separated so that held-out outputs cannot be used to silently modify the tested candidate and then be recounted as unseen.

### Claim boundaries are recorded with results

Synthetic controller evidence, replay evidence, and interactive long-horizon model evidence are treated as different evidence classes. A stronger downstream claim is not inferred from a weaker upstream benchmark.

## 6. Why this is an architectural advance over current ACE-S

Current ACE progressive context answers:

> Which remembered information is likely to be relevant now?

The transactional architecture-memory runtime additionally answers:

> Which remembered information is currently valid, committed, provenance-backed, and allowed to control execution?

That changes the system from a retrieval-centered context controller toward a stateful execution runtime.

The distinction is especially important for:

- stale decisions that remain semantically relevant;
- speculative branches containing plausible but rejected changes;
- nested rollback;
- hard constraints that are old but still active;
- proof obligations that move from SATISFIED back to REOPENED;
- ownership changes that ripple through architecture decisions.

## 7. External positioning

The current result should not be described as public memory SOTA.

Large open-source memory systems such as Mem0, Graphiti, Letta, Supermemory, Cognee, and claude-mem have substantially broader production integrations and/or public benchmark coverage. ACE-S has not yet run an identical public harness against those systems.

The current differentiating hypothesis is narrower:

> Most memory systems optimize what to retain or retrieve; ACE-S architecture memory additionally makes execution validity and canonical-state transition semantics first-class.

The next external comparison should therefore use same-harness adapters rather than comparing incompatible headline percentages.

Candidate public evaluation targets after Suite C1:

1. MemoryArena for interdependent agentic tasks;
2. LongMemEval / MemoryBench for generic long-term memory behavior;
3. direct adapters for strong OSS systems where practical.

## 8. Next gate: interactive Suite C1

The next experiment is the main unresolved evidence gate.

Target design:

- 30 fresh held-out tasks;
- 6 strata × 5 tasks;
- three opaque conditions;
- same GPT-5.6 Luna / xhigh evaluator;
- fresh evaluated sessions;
- long sequential interaction with unrelated distractors;
- intermediate probes plus final action decisions;
- raw outputs frozen before mapping reveal and scoring.

Primary failure classes:

- `FORGOT_HARD_CONSTRAINT`
- `USED_SUPERSEDED_DECISION`
- `ABORTED_BRANCH_CONTAMINATION`
- `PROOF_OBLIGATION_BYPASS`
- `WRONG_STATE_OWNER`
- `PROVENANCE_BREAK`
- `HANDOFF_LOSS`
- `OVER_CONTEXT_DISTRACTION`

The transactional hybrid is promoted from leading candidate only if it preserves or improves task success while reducing stale/speculative-state failures without a material task-stratum regression.

## 9. Current research status

```text
Selective policy/context routing
        |
        v
Typed architecture state graph
        |
        v
Transactional typed hybrid candidate
        |
        +--> Fresh deterministic OOD: PASS
        |
        +--> Blind Luna replay: PASS
        |
        +--> Interactive harness calibration: PASS (execution only)
        |
        v
Interactive Suite C1: NEXT
        |
        v
Public same-harness comparison: PENDING
```

## 10. Claim boundary at this milestone

Supported:

- The frozen transactional typed hybrid passed the synthetic architecture-memory quality gate.
- In the frozen blind Luna replay, the hybrid outperformed current ACE progressive and full-history baselines on exact task success and component correctness.
- The architecture explicitly separates historical memory, speculative state, canonical truth, proof obligations, and worker-visible context.

Not yet supported:

- General public SOTA memory claims.
- A claim that the underlying model's intrinsic memory has improved.
- A claim that the hybrid wins arbitrary real coding-agent workloads.
- A same-harness win over Mem0, Graphiti, Letta, Supermemory, Cognee, claude-mem, or other public systems.

Those claims remain downstream of Suite C1 and public benchmark adapters.
