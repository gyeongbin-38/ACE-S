# Specialization Gate Bench v0.1

> **Evidence level:** development-time controller-mechanics screening only.
>
> The fixtures were authored to exercise the candidate architecture. This is **not** an unseen natural-language routing benchmark and does not measure end-to-end answer quality.

## Question

Should every ACTIVE task be forced into a specialist source domain, or should ACE-S first decide whether specialization is justified?

Three controller conditions were compared across the same 24 mechanics fixtures:

| Condition | Meaning |
|---|---|
| **A — Full Load** | Load GENERIC, every specialist domain, every modifier, and resolution policy for each ACTIVE task. |
| **D — Forced Specialized** | Every ACTIVE task must enter CODE / DOCUMENT / RESEARCH / STATE even when no specialist clearly dominates. |
| **E — Optional Specialization** | ACTIVE first chooses SPECIALIZED vs GENERIC; GENERIC loads no specialist by default and may specialize later. |

## Results

| Metric | A — Full Load | D — Forced Specialized | **E — Optional Specialization** |
|---|---:|---:|---:|
| Specialization Gate Score | 75.0 | 45.3 | **95.7** |
| Mechanical policy coverage | **100.0%** | 50.0% | **100.0%** |
| Clear specialist-task preservation | **100.0%** | **100.0%** | **100.0%** |
| Pure generic tasks with no specialist load | 0.0% | 0.0% | **100.0%** |
| Wrong-specialist → GENERIC recovery | **100.0%*** | 0.0% | **100.0%** |
| Mean policy bytes | 32,634.3 | **14,046.5** | **14,179.2** |
| Mean loaded files | 16.00 | 4.83 | **4.75** |
| Irrelevant policy byte rate | 57.5% | 9.2% | **2.1%** |
| Quality-adjusted policy-byte efficiency | 0.0% | 28.5% | **56.6%** |

\* Full Load contains every policy including GENERIC, so its nominal recovery coverage is mechanically complete but not selective recovery.

Relative to Full Load, Optional Specialization preserves the same oracle-defined mechanics coverage while loading approximately **56.5% fewer policy bytes** on average and reducing irrelevant policy bytes from **57.5% to 2.1%**.

## Family breakdown — Optional Specialization

| Family | n | Mechanical success | Mean policy bytes |
|---|---:|---:|---:|
| Direct | 4 | **100.0%** | 6,311.0 |
| Clear specialized | 8 | **100.0%** | 14,647.8 |
| Generic artifact | 4 | **100.0%** | 14,746.0 |
| Generic history | 3 | **100.0%** | 17,629.7 |
| GENERIC → late specialize | 3 | **100.0%** | 16,597.0 |
| Wrong specialist → GENERIC recovery | 2 | **100.0%** | 18,106.0 |

## What the mechanics experiment supports

The development fixture supports this candidate control shape:

```text
ACTIVE
  ↓
Specialization Gate
  ├─ SPECIALIZED
  │    → one domain manifest
  │    → one specialist
  │    → lazy modifiers
  │
  └─ GENERIC
       → no specialist by default
       → one concrete target/capability
       → lazy modifiers
       → specialize later only if structure emerges
```

The important improvement is not that `GENERIC` knows more things. It deliberately knows **less**: it is a non-specialist entry mode that prevents an ACTIVE task from being forced into a false source domain.

## Failure model

The architecture keeps two bounded recovery directions:

1. a specialist candidate mismatches → return to GENERIC or one retained backup;
2. GENERIC inspection reveals a clear source structure → specialize once into CODE / DOCUMENT / RESEARCH / STATE.

Neither recovery path permits loading all policies for confidence.

## What this result does not prove

The 95.7 score is **not** evidence that a model can reliably decide SPECIALIZED vs GENERIC from arbitrary natural language. The fixtures and candidate were developed in the same design cycle.

The next required gate is a new external holdout selected **after freezing the candidate policy**. The holdout must measure both failure directions:

- `forced_specialization`: choosing a specialist when GENERIC is appropriate;
- `generic_overuse`: choosing GENERIC when a specialist clearly dominates.

Only after that should this architecture replace the frozen forced-primary candidate.

Fixture: [`specialization-gate-bench-v0.1.json`](specialization-gate-bench-v0.1.json)  
Runner: [`../scripts/run_specialization_gate_bench.py`](../scripts/run_specialization_gate_bench.py)
