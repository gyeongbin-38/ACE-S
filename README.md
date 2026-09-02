<div align="center">

# ACE-S

### Adaptive Context Engineering Skill

**Give AI agents the right context, at the right resolution, only when they need it.**

[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-portable-6f42c1)](skills/adaptive-context-engineering/SKILL.md)
![Version](https://img.shields.io/badge/version-0.2.0--alpha-orange)
[![RepoReplay](https://img.shields.io/badge/RepoReplay-90.2%2F100-brightgreen)](benchmarks/POPULAR_REPO_REPLAY.md)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

</div>

ACE-S is a portable **meta-skill for context selection**. It decides whether an agent should retrieve anything at all, which source or structure to inspect first, what fidelity to load, and when enough evidence has been gathered.

It is **not** a vector database, memory server, or replacement for your agent framework. It is the policy layer that tells the agent how to use whatever context tools it already has.

---

## ACE-S in 30 seconds

```text
                         USER TASK
                            │
                            ▼
                 ┌────────────────────┐
                 │ Context sufficient? │
                 └─────────┬──────────┘
                       YES │ NO
              ┌────────────┘ └─────────────┐
              ▼                            ▼
         ANSWER DIRECTLY             CLASSIFY PROBLEM
      (no retrieval cost)                  │
                                           ▼
                           ┌──────────────────────────┐
                           │ smallest useful scope    │
                           │ path / symbol / index    │
                           │ structure / lexical      │
                           └────────────┬─────────────┘
                                        ▼
                              RESOLUTION LADDER
                          index → summary → extract → raw
                                        │
                                        ▼
                                SUFFICIENCY GATE
                           enough? ── yes ──► ANSWER
                              │
                              no
                              ▼
                     EXPAND ONE NARROW STEP
```

The core idea is simple:

> **Do not maximize context. Maximize sufficient, trustworthy context.**

---

## Why use it?

Long-context agents fail in two opposite directions:

| Failure | What happens | ACE-S response |
|---|---|---|
| **Too little context** | missing dependency, stale assumption, unsupported claim | expand the narrowest relevant scope |
| **Too much context** | distraction, tool overload, latency, higher cost | stop early; load only the useful route |
| **Wrong resolution** | summaries hide exact contracts or numbers | escalate to extract/raw evidence |
| **Wrong source** | semantic search misses structural relationships | prefer path/symbol/graph structure when available |
| **Stale state** | old and new facts are silently merged | use temporal/conflict route |
| **Long workflow drift** | useful evidence is discarded too early | preserve future-utility state |

ACE-S is designed to stay out of the way on simple questions. **No retrieval is a valid action.**

---

# Benchmark

## Popular Repo Replay — 21 real bug fixes

We replayed **21 real upstream bug-fix tasks across 7 widely used open-source repositories** using published holdout fixtures with real commit SHAs and ground-truth files:

`Requests` · `Django` · `Zod` · `Actix Web` · `Gson` · `Gin` · `Kubernetes`

The replay used live GitHub code search on the repositories' current default branches. A single-pass baseline gets one condensed lexical search. ACE-S may use up to three retrieval rounds, but can only expand from information surfaced by the previous round (symbol, module, test sibling, package, or exact path hint).

```text
Exact target localization

ACE-S adaptive route     20 / 21  ███████████████████░  95.2%
Single-pass baseline     13 / 21  ████████████░░░░░░░░  61.9%
Canonical target         21 / 21  ████████████████████  100.0%*

* One Gson fixture moved from $Gson$Types.java to GsonTypes.java on the live branch.
```

| Metric | Single-pass | **ACE-S** |
|---|---:|---:|
| Exact target localized | 13 / 21 | **20 / 21** |
| Canonical target localized | 14 / 21 | **21 / 21** |
| Cross-repo coverage | 5 / 7 | **7 / 7** |
| Mean retrieval rounds | 1.00 | **1.38** |
| Maximum retrieval rounds | 1 | **3** |
| RepoReplay Score | **72.9 / 100** | **90.2 / 100** |

### RepoReplay Score

The score is intentionally simple and published:

```text
RepoReplay Score =
  0.60 × exact localization rate
+ 0.25 × retrieval-round efficiency (100 / mean rounds)
+ 0.15 × cross-repo coverage
```

Per-repository results, all 21 fixtures, exact queries, and caveats are in [`benchmarks/POPULAR_REPO_REPLAY.md`](benchmarks/POPULAR_REPO_REPLAY.md) and [`benchmarks/results/live-github-replay-v0.2.csv`](benchmarks/results/live-github-replay-v0.2.csv).

> **Important:** this is a retrieval-policy replay, not an end-to-end model quality benchmark. It does not prove a 90.2% answer accuracy rate or a fixed token saving for every agent.

---

## Same fixture family: coding-specific systems

The same 21-task fixture family is also used by `context-router` for a stronger **pinned-commit, locally indexed coding benchmark**. Those conditions are not identical to ACE-S's live/no-index replay, so the numbers should not be treated as a strict leaderboard.

| System | Execution | Published localization result | Context metric |
|---|---|---:|---:|
| **ACE-S** | live GitHub, no local index, adaptive policy | **20/21 exact; 21/21 canonical** | 1.38 retrieval rounds avg |
| **context-router v4.5** | pinned commits + local index + parent diff | **21/21 rank-1** | 15,325 estimated E2E tokens |
| **code-review-graph 2.3.2** | same context-router comparison setup | 16/21 rank-1 | 380,260 estimated E2E tokens |

`context-router` is the stronger tool when you specifically want a local structural code-context engine. ACE-S is trying to solve the broader problem: **which context strategy should the agent use in the first place?**

See [`benchmarks/COMPETITORS.md`](benchmarks/COMPETITORS.md).

---

# Where ACE-S fits

Different context projects solve different layers. They are often complementary rather than interchangeable.

| Project | Primary strength | Context routing | Code structure | Tool discovery | Persistent memory | Plan-aware | Zero-infra skill |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **ACE-S** | adaptive meta-controller | ● | ◐ | ◐ | — | ● | ● |
| **context-router** | structural code context packs | ◐ | ● | — | — | ◐ | — |
| **Ratel** | dynamic tool/skill discovery | ◐ | — | ● | ◐ | — | — |
| **Acontext** | skill-native persistent memory | ◐ | — | ◐ | ● | — | — |
| **memahead** | plan-aware context compression | ◐ | — | ● | — | ● | — |
| **xMemory** | hierarchical long-term memory retrieval | ● | — | — | ● | — | — |
| **Context Optimization Skills** | masking/cache/compaction tactics | ◐ | — | ◐ | ◐ | — | ● |

`●` native focus · `◐` partial/policy-level support · `—` not the project's primary job

### Strong combinations

```text
ACE-S + context-router  → adaptive policy + strong code graph backend
ACE-S + Ratel           → adaptive policy + large tool/skill discovery
ACE-S + Acontext        → adaptive policy + persistent skill memory
ACE-S + memahead        → adaptive policy + explicit plan-aware compression
```

---

# The 7 rules

1. **No Retrieval Is an Action** — if current context is sufficient, answer directly.
2. **Route Before Retrieve** — classify the context problem before loading more data.
3. **Resolution Before Volume** — index → summary → extract → raw.
4. **Structure Before Global Search** — when paths, symbols, dependencies, or hierarchy exist, use them.
5. **Future Utility Matters** — keep information that later workflow steps will need.
6. **Summary Is a View, Not Truth** — preserve a route back to raw evidence.
7. **Expand on Insufficiency** — not merely because a token threshold was reached.

Priority:

```text
correctness & completeness
        > provenance & recoverability
        > context efficiency
        > latency
```

---

# Install

With the open `skills` CLI:

```bash
npx skills add gyeongbin-38/ACE-S-adaptive-context-engineering-skill \
  --skill adaptive-context-engineering
```

The skill itself has no required vector database, embedding model, API key, or background service.

### Skill layout

```text
skills/adaptive-context-engineering/
├── SKILL.md                  # small router / activation policy
├── references/
│   ├── coding.md             # structural repo route
│   ├── temporal.md           # changing/conflicting state
│   ├── research.md           # multi-source research
│   ├── plan-aware.md         # future-utility retention
│   ├── resolution-ladder.md  # progressive fidelity
│   └── evidence-and-provenance.md
└── evals/
    └── evals.json
```

Only the relevant specialist reference should be loaded for the current task. **The skill uses progressive disclosure on itself.**

---

# Daily use

ACE-S is most useful for:

- deep research and multi-source synthesis;
- repository investigation and code changes;
- long PDFs/documents and large tool outputs;
- long-running workflows and handoffs;
- conflicting or changing project state;
- exact contracts, numbers, APIs, and provenance-sensitive tasks.

It should normally stay dormant for:

- short factual questions already answerable from context;
- casual conversation;
- creative writing;
- simple transformations where no extra evidence is needed.

---

# Benchmark policy

We separate three evidence levels:

1. **Synthetic mechanism benchmark** — architecture screening only.
2. **Live public-repo replay** — real repositories and real ground-truth files, but not a model-quality test.
3. **End-to-end agent A/B** — same model/task with ACE-S OFF vs ON. This is required before claiming general answer-quality or token improvements.

We intentionally publish misses and caveats. See [`benchmarks/`](benchmarks/).

---

## Status

**v0.2.0-alpha** — public research alpha.

Next release gate: reproducible Codex / Claude Code / OpenCode A/B evaluation with pass rate, trigger precision, input tokens, latency, and failure categories.

## License

MIT
