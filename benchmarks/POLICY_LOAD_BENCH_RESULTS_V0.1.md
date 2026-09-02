# Selective Policy Load Bench v0.1

> **Evidence level:** controller-mechanics benchmark only.
>
> This benchmark uses oracle-authored domain/modifier requirements. It measures whether a policy-loading architecture can remain selective, compose lazy policies, and recover from a wrong first candidate. It does **not** measure natural-language routing accuracy, model reasoning quality, or end-to-end answer quality.

## Research question

Must ACE-S load its whole architecture to make reliable context decisions, or can it progressively load only the policy needed for the current subproblem and recover when the first coarse guess is wrong?

Four controller conditions were run on the same 28 fixtures:

| Condition | Behavior |
|---|---|
| **A — Full Load** | Keep the tiny kernel, then load every manifest and specialist policy for every active task. |
| **B — Hard Single** | Load only the first candidate domain. No lazy modifiers and no recovery. |
| **C — Progressive / No Recovery** | Load one domain and only required lazy modifiers, but a wrong first candidate is fatal. |
| **D — Progressive + Recovery** | Load one domain, lazy-load newly material policies, and allow one bounded backup recovery path. |

Fixture families:

- direct/no-policy tasks;
- single-domain tasks;
- lazy-modifier tasks;
- wrong-first candidate rejected at the manifest boundary;
- wrong-first candidate rejected only after specialist no-progress;
- compositional tasks requiring several policies over time.

## Headline results

| Condition | Selective Load Score | Mechanical success | Wrong-first recovery | Active false-stop | Mean policy bytes | Mean loaded files | Irrelevant policy bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| **A — Full Load** | 82.5 | **100.0%** | **100.0%** | **0.0%** | 29,899.6 | 15.57 | 53.8% |
| **B — Hard Single** | 34.2 | 28.6% | 0.0% | 83.3% | **9,687.5** | **3.36** | 6.6% |
| **C — Progressive / No Recovery** | 67.3 | 71.4% | 0.0% | 33.3% | 12,394.1 | 4.89 | 5.2% |
| **D — Progressive + Recovery** | **98.6** | **100.0%** | **100.0%** | **0.0%** | **14,457.1** | **6.04** | **4.4%** |

Under this controller-mechanics setup, D preserves A's 100% oracle-defined mechanical coverage while loading approximately **51.6% fewer policy bytes** and **61.2% fewer policy files on average**. Its irrelevant-policy byte rate falls from **53.8% to 4.4%** (-49.4 percentage points).

These numbers are **architecture-mechanics results**, not claims that a model will obtain 100% routing or answer accuracy.

## Policy size snapshot

Measured from the repository files at benchmark time:

| Component | Bytes |
|---|---:|
| Tiny `SKILL.md` kernel | 5,393 |
| Manifest index | 2,089 |
| All domain/modifier manifests | 6,494 |
| All specialist references used by the benchmark | 20,008 |

This is why policy itself must be treated as context: eager policy loading can dominate the context budget before task evidence is even retrieved.

## Condition analysis

### A — Full Load

A never misses an oracle-required policy, but it pays for that reliability by loading nearly the entire policy graph for every active task.

- success: 100%
- mean policy bytes: 29.9 KB
- mean files: 15.57
- irrelevant policy bytes: 53.8%

This is the safety-through-overloading baseline. It is reliable mechanically but conflicts with ACE-S's own progressive-context principle.

### B — Hard Single

B is cheap but brittle.

- success: 28.6%
- active false-stop: 83.3%
- lazy-modifier success: 0%
- compositional success: 0%
- wrong-first recovery: 0%

The result demonstrates why a single irreversible route decision is not sufficient for mixed or evolving tasks.

### C — Progressive without recovery

C successfully handles all direct, single-domain, lazy-modifier, and compositional fixtures when the first candidate is correct.

- direct: 100%
- single-domain: 100%
- lazy-modifier: 100%
- compositional: 100%
- wrong-first manifest: 0%
- wrong-first specialist: 0%

The first routing decision remains a single point of failure. Progressive disclosure alone is not enough.

### D — Progressive with bounded recovery

D recovers both kinds of wrong-first routing:

1. **manifest reject** — mismatch is detected before loading the wrong specialist;
2. **specialist no-progress** — the wrong specialist was plausibly loaded, but lack of progress triggers one backup switch.

D does not recover by fanning out across every policy. The candidate budget remains one primary plus at most one backup.

Family means:

| Fixture family | Success | Mean policy bytes | Mean files |
|---|---:|---:|---:|
| Direct | 100% | 5,393.0 | 1.00 |
| Single domain | 100% | 10,942.8 | 4.00 |
| Lazy modifier | 100% | 14,023.2 | 5.67 |
| Wrong-first manifest | 100% | 14,788.8 | 6.50 |
| Wrong-first specialist | 100% | 19,092.5 | 8.50 |
| Compositional | 100% | 19,965.2 | 9.17 |

The specialist-no-progress cases cost more than manifest-level rejection, which is expected: the system has already paid to inspect one wrong specialist before recovery. This makes **early mismatch detection valuable, but not mandatory for correctness**.

## Score

```text
Selective Load Score =
  0.45 × mechanical task success
+ 0.20 × quality-adjusted policy-byte efficiency
+ 0.15 × selective purity
+ 0.10 × recoverable wrong-first success
+ 0.10 × active no-false-stop
```

The score is intended for architecture screening only. A high score cannot compensate for a future real-agent quality regression.

## What this benchmark supports

The experiment supports the following **controller architecture hypothesis**:

```text
Tiny Kernel
  → coarse candidate
  → one manifest
  → one specialist
  → minimal retrieval
  → sufficiency
      ├─ continue current policy
      ├─ lazy-load one newly material policy
      ├─ bounded switch to one backup/new candidate
      └─ stop
```

It does **not** support the stronger claim that a frontier model will reliably infer the correct initial candidate or the right time to switch policies.

## Next evidence gate

Before this architecture becomes a stable v0.4 claim:

1. freeze this controller behavior;
2. author a separate unseen natural-language routing/recovery suite without tuning against it;
3. run repeated model predictions and publish raw outputs;
4. run same-model end-to-end ACE-S OFF vs progressive-policy ON tasks;
5. require final quality to be preserved before counting policy/context savings.

Source fixtures: [`policy-load-bench-v0.1.json`](policy-load-bench-v0.1.json)  
Runner: [`../scripts/run_policy_load_bench.py`](../scripts/run_policy_load_bench.py)
