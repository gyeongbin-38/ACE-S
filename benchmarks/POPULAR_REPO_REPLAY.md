# ACE-S Popular Repo Replay

**Version:** v0.2.0-alpha  
**Run date:** 2026-09-02  
**Purpose:** test whether ACE-S's adaptive retrieval policy can localize relevant code context on real, widely used repositories without a local index.

## Dataset

The task set reuses the public holdout fixtures from [`mohankrishnaalavala/context-router`](https://github.com/mohankrishnaalavala/context-router/tree/main/benchmark/holdout).

Each fixture contains a **real upstream commit SHA**, a natural-language debugging/implementation query, and the production file touched by the fix.

| Repository | Language / scale | Tasks |
|---|---|---:|
| `psf/requests` | Python | 3 |
| `django/django` | Python | 3 |
| `colinhacks/zod` | TypeScript | 3 |
| `actix/actix-web` | Rust | 3 |
| `google/gson` | Java | 3 |
| `gin-gonic/gin` | Go | 3 |
| `kubernetes/kubernetes` | Go / very large monorepo | 3 |
| **Total** | 5 language families | **21** |

## Execution environment

This replay was performed through live GitHub code search against each repository's **current default branch**.

The environment used for the run could not clone public repositories, so this is deliberately called a **live replay**, not a reproduction of context-router's pinned local-index benchmark.

### Baseline

One retrieval round using a compact lexical query derived from the task wording.

No follow-up is allowed.

### ACE-S treatment

Maximum three rounds.

1. Start with the smallest useful lexical/symbol query.
2. If insufficient, use only information surfaced by the previous round:
   - exact symbol/function/class,
   - module/package,
   - test sibling,
   - changelog/issue clue,
   - documentation path hint.
3. Expand one narrow step.
4. Stop immediately once the production target is sufficiently localized.

The treatment is intentionally consistent with the shipped [`coding.md`](../skills/adaptive-context-engineering/references/coding.md) and [`SKILL.md`](../skills/adaptive-context-engineering/SKILL.md).

## Results

| Repository | Single-pass exact | ACE-S exact | ACE-S canonical | Mean ACE-S rounds |
|---|---:|---:|---:|---:|
| Requests | 1 / 3 | **3 / 3** | 3 / 3 | 1.67 |
| Django | 1 / 3 | **3 / 3** | 3 / 3 | 1.67 |
| Zod | 2 / 3 | **3 / 3** | 3 / 3 | 1.33 |
| Actix Web | 3 / 3 | **3 / 3** | 3 / 3 | 1.00 |
| Gson | 2 / 3 | 2 / 3 | **3 / 3** | 1.00 |
| Gin | 2 / 3 | **3 / 3** | 3 / 3 | 1.33 |
| Kubernetes | 2 / 3 | **3 / 3** | 3 / 3 | 1.67 |
| **Total** | **13 / 21 (61.9%)** | **20 / 21 (95.2%)** | **21 / 21 (100%)** | **1.38** |

The Gson exception is historical path drift: the fixture targets `gson/src/main/java/com/google/gson/internal/$Gson$Types.java`, while the current default branch surfaces the equivalent `GsonTypes.java` module. We count it as a canonical target hit but **not** as an exact historical-path hit.

## Score

To keep the headline score reproducible, ACE-S uses a fixed formula for this replay:

```text
RepoReplay Score =
  0.60 × exact localization rate
+ 0.25 × retrieval-round efficiency
+ 0.15 × cross-repo coverage

retrieval-round efficiency = 100 / mean retrieval rounds

cross-repo coverage = percentage of repositories where
at least 2 of 3 tasks are exactly localized
```

### ACE-S

```text
Exact localization       = 95.2381
Round efficiency         = 72.4138   (100 / 1.38095)
Cross-repo coverage      = 100.0000

Score = 0.60(95.2381) + 0.25(72.4138) + 0.15(100)
      = 90.2463
      ≈ 90.2 / 100 (one decimal place)
```

### Single-pass baseline

```text
Exact localization       = 61.9048
Round efficiency         = 100.0000
Cross-repo coverage      = 71.4286

Score = 72.8571
      ≈ 72.9 / 100
```

The score intentionally penalizes ACE-S for extra retrieval rounds. A policy does not get free credit for endlessly searching until it finds the answer.

## Interesting cases

### Requests — netrc

A broad query surfaced `tests/test_utils.py`, which exposed the exact `get_netrc_auth` symbol. One symbol follow-up localized `src/requests/utils.py`.

This is the intended ACE-S pattern:

```text
query → relevant test → exact symbol → production implementation → stop
```

### Django — `orderby_issubset_groupby`

The initial compound query returned no results. Removing descriptive noise and using the exact property name localized `django/db/models/sql/query.py` immediately.

```text
verbose query → insufficient → exact symbol → target
```

### Kubernetes — current-context write location

This was the hardest replay case and used all three allowed rounds:

```text
kubectl config clue
      ↓
clientcmd package
      ↓
loader_test.go
      ↓ structural sibling
loader.go
```

The test demonstrates why ACE-S prefers **local structure after a useful seed** instead of repeating global semantic search.

## Comparison to context-router

`context-router` publishes a stronger coding-specific benchmark using the same 21-task fixture family under a different setup:

- pinned repository snapshots;
- local symbol/edge index;
- `parent-sha-with-diff` anchor;
- 21/21 rank-1 hits;
- 15,325 estimated end-to-end tokens.

Its comparison arm, `code-review-graph 2.3.2`, reports 16/21 rank-1 hits and 380,260 estimated end-to-end tokens.

Source: [`context-router/BENCHMARKS.md`](https://github.com/mohankrishnaalavala/context-router/blob/main/BENCHMARKS.md).

These are **not apples-to-apples performance numbers**. context-router is a local code-context engine; ACE-S is a portable policy skill running without that index. The useful comparison is architectural:

- If the task is purely repository context construction and local indexing is available, context-router is a stronger specialized backend.
- If the agent needs a portable rule for deciding *whether and how* to retrieve across code, research, history, plans, and evidence, ACE-S addresses a broader layer.
- They can be used together: ACE-S can route a code task into context-router.

## Limitations

1. **Not blinded.** The fixture set is public. This is a replay of a policy, not a hidden test set.
2. **Current branches, not pinned snapshots.** Historical paths may have moved, as seen in Gson.
3. **No model answer judge.** The metric is context localization, not bug-fix correctness.
4. **No directly comparable token metric.** GitHub connector response accounting is not equivalent to context-router's local pack/downstream token estimator.
5. **Small task count.** 21 tasks are useful for a first real-repo stress test, not a claim of universal superiority.
6. **Human/LLM policy execution.** Follow-up query selection follows ACE-S rules but is not yet generated by a deterministic standalone benchmark runner.

## Next benchmark

The stable-release gate is an end-to-end A/B suite:

```text
same task + same model + same tools

ACE-S OFF  vs  ACE-S ON

measure:
- task pass rate / pass@k
- trigger precision and false activation
- input tokens
- tool calls
- latency
- evidence correctness
- failure category
```

Candidate harnesses: Codex, Claude Code, and OpenCode.

## Raw results

[`results/live-github-replay-v0.2.csv`](results/live-github-replay-v0.2.csv)
