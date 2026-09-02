# ACE-S Benchmarks

ACE-S separates benchmark evidence into levels so architecture-selection numbers are not confused with real model-quality claims.

## Evidence ladder

```text
Level 1  Synthetic mechanism simulation
         ↓
Level 2  Real public-repository replay
         ↓
Level 3  Same-model end-to-end A/B agent evaluation
```

Only Level 3 can support broad claims about answer quality, token savings, or latency for a particular agent/model.

---

## Level 1 — Synthetic mechanism benchmark

File: [`results/synthetic-v0.1.csv`](results/synthetic-v0.1.csv)

Purpose: screen context-management architectures before shipping the skill.

Workload:

- 3 independent random seeds;
- 14 context-task classes;
- 2K / 8K / 32K working-context budgets;
- 40 cases per class/budget/seed;
- 65,520 strategy evaluations across the full experiment series.

Task classes included simple recent context, exact fact recovery, conflicting state, long documents, research synthesis, multi-source verification, local code, code ripple, multi-step plans, tool selection, noisy chat, aggregation, historical/temporal state, and no-retrieval controls.

Main architecture result: a **small router + conditional specialist references** beat a monolithic always-loaded context skill in the simulator.

This is a mechanism simulator, **not an end-to-end LLM benchmark**.

---

## Level 2 — Popular Repo Replay

Main report: [`POPULAR_REPO_REPLAY.md`](POPULAR_REPO_REPLAY.md)  
Raw results: [`results/live-github-replay-v0.2.csv`](results/live-github-replay-v0.2.csv)

21 real upstream bug-fix fixtures across:

- Requests
- Django
- Zod
- Actix Web
- Gson
- Gin
- Kubernetes

Headline:

| Metric | Single-pass | **ACE-S** |
|---|---:|---:|
| Exact target localization | 13/21 (61.9%) | **20/21 (95.2%)** |
| Canonical target localization | 14/21 | **21/21** |
| Mean retrieval rounds | 1.00 | **1.38** |
| RepoReplay Score | 72.9/100 | **90.3/100** |

The replay used live GitHub code search on current default branches. It is a context-localization test, not a bug-fix correctness test.

---

## Related / competitor evidence

See [`COMPETITORS.md`](COMPETITORS.md).

Direct same-fixture evidence exists for the coding-specific `context-router` benchmark. Other projects such as Ratel, Acontext, memahead, and xMemory solve different layers, so their own published benchmark results are shown with their original scope rather than merged into a fake universal leaderboard.

---

## Level 3 — End-to-end A/B release gate

Still required before `v1.0` performance claims.

Experimental design:

```text
same model
same task
same tools
same starting repository / documents

control: ACE-S OFF
vs
 treatment: ACE-S ON
```

Report:

- pass rate / pass@k;
- trigger precision and recall;
- false activation rate;
- input tokens;
- tool calls;
- wall-clock latency;
- exact-evidence correctness;
- failure category;
- negative/no-uplift cells.

Target harnesses: Codex, Claude Code, and OpenCode (or another reproducible coding-agent runner).

## Reporting policy

1. Publish misses and regressions.
2. Never present synthetic scores as model scores.
3. Never compare token numbers produced by incompatible accounting methods as if they were identical.
4. Record repository refs, task fixtures, prompts, model versions, and run dates.
5. Prefer paired same-task comparisons.
6. Quality first; efficiency second.
