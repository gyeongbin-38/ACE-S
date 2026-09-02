# ACE-S RouterBench v0.1 — Exploratory Historical Result

> **Status: exploratory / not a stable routing-performance claim.**
>
> The signal-aware policy and the stress prompts were developed in the same experiment cycle. The resulting scores are useful for architecture exploration and failure discovery, but leakage/overfitting is plausible. Do not present the 92.9 / 97.8 values as frontier-model accuracy or general ACE-S performance.

Date: 2026-09-02  
Original CI run: https://github.com/gyeongbin-38/ACE-S/actions/runs/33594790470

## What was tested

Three deterministic policy prototypes were evaluated on authored routing fixtures:

| Condition | Description |
|---|---|
| **A — Legacy Flat** | v0.3-style overloaded single-route precedence. |
| **B — Layered Naive** | Domain/modifier separation with naive surface-cue activation. |
| **C — Layered Signal-Aware** | Domain/modifier separation plus explicit negative/near-miss boundaries. |

Two 20-case suites were used:

- Primary: `routerbench-v0.1.json`
- Stress: `routerbench-stress-v0.1.json`

The stress set was separate from the primary file, but it was **not a blinded holdout**.

## Historical scores

| Condition | Primary score | Stress score | Primary exact | Stress exact | Over-trigger |
|---|---:|---:|---:|---:|---:|
| **A — Legacy Flat** | 62.7 | 61.2 | 30.0% | 25.0% | 0.0% |
| **B — Layered Naive** | 78.2 | 84.6 | 25.0% | 55.0% | 40.0% |
| **C — Layered Signal-Aware** | **92.9** | **97.8** | **75.0%** | **90.0%** | **0.0%** |

These numbers showed that the representation could encode mixed concerns better than a single overloaded route, and that naive layering can badly over-trigger. They did **not** establish general model routing accuracy.

## Why the architecture changed afterward

The experiment exposed a deeper problem: making the global classifier more detailed can improve authored-fixture scores while recreating the same context-overload problem inside ACE-S itself.

The v0.4 development architecture therefore moved from:

```text
read all route criteria
→ classify every domain/modifier/fidelity dimension
→ execute
```

toward:

```text
Tiny Kernel
→ coarse candidate
→ ONE manifest
→ ONE specialist
→ retrieve minimal context
→ sufficiency
   ├─ continue
   ├─ lazy-load one newly material policy
   └─ bounded recovery to one backup/new candidate
```

This makes **policy itself subject to progressive disclosure**.

## Useful failures retained from this experiment

The early benchmark still provides useful regression examples:

- lexical `current/latest/version` cues must not automatically imply time-sensitive retrieval;
- tool discovery should normally start from capability/index metadata rather than source bodies;
- a single route cannot naturally represent compositional work;
- a hard first routing decision needs a recovery path;
- mixed tasks are better treated as policies that become material over time than as a requirement to predict every modifier at task start.

## Replacement architecture-mechanics benchmark

For v0.4 architecture screening, use:

[`POLICY_LOAD_BENCH_RESULTS_V0.1.md`](POLICY_LOAD_BENCH_RESULTS_V0.1.md)

That benchmark deliberately **does not test natural-language classification**. It uses oracle requirements to isolate policy-loading and recovery mechanics.

## Next valid routing evidence

A stable routing claim requires:

1. a frozen policy/controller before test prompt authoring;
2. independently authored or blinded natural-language prompts;
3. repeated predictions across target models/agent surfaces;
4. raw prediction publication;
5. candidate recall, recovery rate, false policy loads, policy tokens/bytes, and downstream quality;
6. end-to-end ACE-S OFF vs ON evaluation before claiming general answer-quality or context-efficiency gains.

The defensible conclusion from RouterBench v0.1 is therefore limited to:

> The authored deterministic experiment helped reveal weaknesses of flat routing and naive layering, but its high signal-aware scores are not suitable as a stable performance claim.
