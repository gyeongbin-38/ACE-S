# ACE-S Roadmap

ACE-S is currently a public research alpha. The roadmap is organized around **evidence gates**, not feature count.

## v0.3 — Operational depth

Status: substantially complete; awaiting external/real-agent validation

- [x] Add a dedicated long-document route.
- [x] Expand research routing into claim-centered retrieval and explicit sufficiency criteria.
- [x] Expand plan-aware retention and handoff state.
- [x] Expand evidence/provenance rules with fidelity classes and recoverable source chains.
- [x] Publish the end-to-end agent A/B protocol.
- [x] Add a practical Quickstart.
- [x] Add negative evals for over-triggering, premature raw loading, over-retention, and trust-boundary failures.
- [x] Add experimental context-state contract examples for long-running tasks.
- [ ] Add executable/adapted integration examples for major agent surfaces.

## v0.4 — Real-agent evaluation

Release gate: reproducible same-model OFF vs ON results.

- [ ] Codex A/B benchmark.
- [ ] Claude Code A/B benchmark.
- [ ] OpenCode A/B benchmark.
- [ ] Report verified success, input/output tokens, tool calls, latency, trigger precision, and failure classes.
- [ ] Publish all regressions and no-uplift cases.
- [ ] Add paired statistical analysis when sample size supports it.

## v0.5 — Context controller interface

Goal: make the policy easier to implement in agent runtimes without forcing one backend.

An experimental vocabulary now exists in [`docs/CONTEXT_CONTRACTS.md`](docs/CONTEXT_CONTRACTS.md). It is intentionally **not yet a stable API**.

Candidate controller actions:

```text
DIRECT
ROUTE
FETCH
EXPAND
PIN
OFFLOAD
REOPEN_RAW
COMPACT
STOP
```

Stabilization work:

- [ ] Validate the draft `ContextDecision` fields across multiple agent surfaces.
- [ ] Validate `EvidencePacket`, `HandoffState`, `SufficiencyReport`, and `WorkingContext` against real A/B traces.
- [ ] Separate policy decisions from retrieval backend implementation in executable adapters.
- [ ] Add adapters/examples for structural code retrieval, persistent memory, and hierarchical stores.
- [ ] Remove fields that do not earn their context/storage cost before freezing a schema.

## v0.6 — Learned/adaptive control experiments

These are experiments, not guaranteed roadmap commitments.

- [ ] Compare static rule controller vs lightweight learned route selection.
- [ ] Test adaptive compaction thresholds driven by task state rather than token count.
- [ ] Test hierarchical navigation on long histories/repositories.
- [ ] Evaluate whether agent-controlled `KEEP / EVICT / FETCH / EXPAND` actions outperform deterministic heuristics.

Adoption requires measured quality preservation.

## Stable 1.0 gate

ACE-S should not be called stable until all of the following hold:

1. activation behavior is reliable across simple and complex tasks;
2. exact/provenance-sensitive tasks show no material fidelity regression;
3. at least one reproducible real-agent benchmark shows a meaningful benefit;
4. failure modes and limitations are documented;
5. installation and use are tested by users other than the original author;
6. benchmark claims can be regenerated from public raw results and scoring code.

## Non-goals

ACE-S does not plan to become:

- a vector database;
- a proprietary memory server;
- a mandatory agent framework;
- a benchmark leaderboard optimized at the expense of correctness;
- a system that assumes more context is always better.

The project should remain portable: a policy/controller that can sit above different context backends.
