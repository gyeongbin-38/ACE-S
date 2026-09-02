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

## v0.4 — Layered context decisions + routing evaluation

Goal: replace the overloaded single-route mental model with a measurable layered controller while preserving the zero-infrastructure Skill form.

Core shape:

```text
Activation
  ↓
Signals
  ↓
Primary domain + modifiers + minimum fidelity
  ↓
Context action
  ↓
Evidence/state
  ↓
Sufficiency + retention
```

Implemented in the v0.4 development branch:

- [x] Split primary domain from cross-cutting modifiers.
- [x] Treat `TEMPORAL`, `EVIDENCE_CRITICAL`, `PLAN_AWARE`, and `TOOL_DISCOVERY` as composable modifiers.
- [x] Clarify that the resolution ladder is a lowest-sufficient-fidelity policy, not a mandatory sequential staircase.
- [x] Add experimental `ContextSignals` and `ContextProjection` contracts.
- [x] Recast `ContextDecision` around explicit controller actions.
- [x] Add an initial RouterBench fixture set with negative, near-miss, mixed-route, and ambiguous cases.
- [x] Add a static RouterBench fixture validator.
- [ ] Expand RouterBench to >=100 prompts.
- [ ] Run repeated routing sweeps across multiple frontier agent/model surfaces.
- [ ] Publish activation precision/recall, domain accuracy, modifier F1, fidelity accuracy, and raw predictions.
- [ ] Add explicit reacquisition-overhead measurement to real-agent traces.

Release gate: no routing claim becomes stable without reproducible raw predictions and disclosed failures.

## v0.5 — Real-agent A/B + controller adapters

Release gate: reproducible same-model OFF vs ON results with quality preservation.

- [ ] Codex A/B benchmark.
- [ ] Claude Code A/B benchmark.
- [ ] OpenCode A/B benchmark.
- [ ] Report verified success, input/output tokens, tool calls, latency, trigger precision, retrieval rounds, reacquisition calls, and failure classes.
- [ ] Publish all regressions and no-uplift cases.
- [ ] Add paired statistical analysis when sample size supports it.
- [ ] Validate `ContextSignals`, `ContextProjection`, `ContextDecision`, `EvidencePacket`, `HandoffState`, `SufficiencyReport`, `RetentionDecision`, and `WorkingContext` against real traces.
- [ ] Separate policy decisions from retrieval backend implementation in executable adapters.
- [ ] Add adapters/examples for structural code retrieval, persistent memory, and hierarchical stores.
- [ ] Remove fields that do not earn their context/storage cost before freezing a schema.

## v0.6 — Adaptive sufficiency and retention experiments

These are experiments, not guaranteed roadmap commitments.

- [ ] Compare deterministic rules vs LLM self-judgment vs lightweight learned sufficiency routing.
- [ ] Test adaptive compaction thresholds driven by task state rather than token count.
- [ ] Test hierarchical navigation on long histories/repositories.
- [ ] Evaluate whether agent-controlled `KEEP / EVICT / FETCH / EXPAND` actions outperform deterministic heuristics.
- [ ] Measure whether compression saves tokens while increasing hidden reacquisition/interaction cost.

Adoption requires measured quality preservation.

## v0.7 — Offline policy evolution experiments

Goal: improve the Skill from benchmark evidence without allowing uncontrolled production self-modification.

Candidate loop:

```text
benchmark traces
  → failure clustering
  → candidate description/policy mutations
  → holdout RouterBench + real-agent A/B
  → human review
  → versioned promotion
```

- [ ] Test failure-driven activation/description rewrites.
- [ ] Test offline mutation of specialist-policy boundaries.
- [ ] Keep production Skill versions deterministic and reproducible.
- [ ] Require holdout improvement before promotion.

## Stable 1.0 gate

ACE-S should not be called stable until all of the following hold:

1. activation behavior is reliable across simple and complex tasks;
2. mixed tasks are represented without forcing incompatible concerns into one route;
3. exact/provenance-sensitive tasks show no material fidelity regression;
4. at least one reproducible real-agent benchmark shows a meaningful benefit;
5. failure modes, no-uplift cases, and limitations are documented;
6. installation and use are tested by users other than the original author;
7. benchmark claims can be regenerated from public raw results and scoring code.

## Non-goals

ACE-S does not plan to become:

- a vector database;
- a proprietary memory server;
- a mandatory agent framework;
- a model-routing gateway;
- a benchmark leaderboard optimized at the expense of correctness;
- a system that assumes more context is always better.

The project should remain portable: a policy/controller that can sit above different context backends.
