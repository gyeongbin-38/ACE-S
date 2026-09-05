# Architecture Memory Suite C1 — Invalidation Report

Status: `INVALID_FOR_ARCHITECTURE_MEMORY_PROMOTION`

Branch: `exp/architecture-memory-runtime-v01`

## Summary

Suite C1 completed its model-execution workload, but the benchmark is invalid for architecture-memory promotion because the evaluation prompts leaked the intended answer structure.

The invalidation is methodological, not a model-execution failure.

## What completed successfully

- 18 / 18 evaluated Luna sessions completed.
- 1,080 / 1,080 sequential turns completed.
- 18 / 18 final model completions existed in the evaluated agent timelines.
- 90 / 90 final task entries existed after timeline recovery.
- No model rerun was used to repair a semantic/model mistake.
- No actual model final was structurally malformed.
- A persistence incident was isolated: Paseo `send` acknowledgements were persisted instead of the evaluated assistant completion for 13 sessions; immutable timeline outputs were recovered without semantic mutation.

These properties make C1 useful as a harness/runner stress test, but not as promotion evidence.

## Invalidation reason

The final evaluation prompts explicitly labeled answer choices with semantic cues such as `current state`, `startup/older state`, and `ignore active constraints/obligations` while also embedding the corresponding state values.

Therefore a model could obtain high action accuracy by following the wording of the option rather than preserving architecture state across the long interaction.

The same issue existed in intermediate probes.

Approximate exposure surface:

- 3 opaque conditions;
- 6 sessions per condition;
- 5 final tasks per session = 90 final task evaluations;
- 10 probes per session = 180 intermediate probes.

Because the answer cue was part of the evaluation surface, final option correctness, probe accuracy, current-state value accuracy, hard-constraint adherence, owner accuracy, and obligation accuracy cannot be promoted as unbiased C1 evidence.

## What remains usable

C1 may still be cited as execution/harness evidence for:

- multi-session orchestration;
- 60-turn sequential delivery;
- fresh-session isolation;
- interrupted-session resume of the original evaluated session;
- raw/timeline provenance handling;
- result persistence failure detection and recovery;
- benchmark validity auditing itself.

C1 must not be used for:

- Transactional Hybrid promotion;
- architecture-memory headline accuracy;
- public SOTA claims;
- comparison against external memory systems.

## Research lesson

Benchmark validity is part of architecture evidence.

A high score is not evidence when the evaluation surface reveals the intended answer. This is the same class of failure previously seen when a Kubernetes replay task used the wrong gold owner: benchmark design and gold provenance must be validated before interpreting model performance.

## Replacement benchmark

Suite C2 replaces C1 with:

- a fresh seed;
- 30 fresh tasks;
- 6 strata × 5 tasks;
- 3 opaque conditions;
- 6 fresh evaluated sessions per condition;
- 60 sequential turns per session;
- free-recall structured probes;
- free-recall structured finals;
- no multiple-choice answer labels;
- no gold/current value in the evaluation query surface;
- a pre-run leakage audit hard gate;
- explicit separation between runner acknowledgement and evaluated assistant timeline completion.

Suite C1 remains permanently invalidated rather than repaired and recounted as held-out evidence.
