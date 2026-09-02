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

## v0.4 — Progressive policy loading + recovery

Goal: make ACE-S apply its own context-engineering principle to **its policy instructions themselves**.

Core shape:

```text
Task
 ↓
Tiny Kernel: DIRECT / ACTIVE / UNCERTAIN
 ↓
Coarse candidate (one + optional backup)
 ↓
Manifest index
 ↓
ONE selected manifest
 ↓
ONE specialist policy
 ↓
minimal context retrieval
 ↓
Sufficiency
 ├─ STOP
 ├─ continue same policy
 ├─ lazy-load one newly material modifier/domain
 └─ bounded recovery to one backup/new candidate
```

Implemented in the v0.4 development branch:

- [x] Shrink the always-loaded skill body into a small context-policy kernel.
- [x] Add a compact manifest index instead of enumerating every specialist procedure in the kernel.
- [x] Split policy into primary-domain manifests and lazy modifier manifests.
- [x] Enforce one-primary-plus-one-backup coarse recognition.
- [x] Make wrong-first-candidate routing recoverable rather than fatal.
- [x] Add explicit `SWITCH_POLICY` / policy-load state contracts.
- [x] Add tool discovery as a lazily loaded policy with metadata/index-first behavior.
- [x] Add Selective Policy Load Bench fixtures and a reproducible controller-mechanics runner.
- [ ] Independently author an unseen natural-language candidate-routing suite.
- [ ] Run repeated routing sweeps across multiple frontier model/agent surfaces.
- [ ] Measure policy tokens/bytes loaded, irrelevant policy load, recovery rate, false stops, retrieval rounds, and end-to-end quality.
- [ ] Validate that progressive loading preserves or improves real-agent task success relative to full-policy loading.

### RouterBench status

The early layered RouterBench experiments remain useful for design exploration, but they are **not a stable performance claim**. The signal-aware policy and stress prompts were developed in the same experiment cycle, so leakage/overfitting is plausible.

Stable routing claims require independently authored or blinded prompts plus raw repeated model predictions.

### Release gate

Do not promote v0.4 based on policy-loading efficiency alone. Quality must be preserved first, and the system must recover from plausible wrong-first routing without falling back to loading every policy.

## v0.5 — Real-agent A/B + controller adapters

Release gate: reproducible same-model OFF vs ON results with quality preservation.

- [ ] Codex A/B benchmark.
- [ ] Claude Code A/B benchmark.
- [ ] OpenCode A/B benchmark.
- [ ] Report verified success, input/output tokens, policy tokens/bytes, tool calls, latency, trigger precision, retrieval rounds, reacquisition calls, and failure classes.
- [ ] Publish all regressions and no-uplift cases.
- [ ] Add paired statistical analysis when sample size supports it.
- [ ] Validate `ContextIntent`, `PolicyLoadState`, `ContextDecision`, `EvidencePacket`, `HandoffState`, `SufficiencyReport`, `RetentionDecision`, and `WorkingContext` against real traces.
- [ ] Separate policy decisions from retrieval backend implementation in executable adapters.
- [ ] Add adapters/examples for structural code retrieval, persistent memory, and hierarchical stores.
- [ ] Remove fields and policies that do not earn their context/storage cost before freezing a schema.

## v0.6 — Adaptive sufficiency and retention experiments

These are experiments, not guaranteed roadmap commitments.

- [ ] Compare deterministic rules vs LLM self-judgment vs lightweight learned sufficiency routing.
- [ ] Test adaptive compaction thresholds driven by task state rather than token count.
- [ ] Test hierarchical navigation on long histories/repositories.
- [ ] Evaluate whether agent-controlled `KEEP / EVICT / FETCH / EXPAND / SWITCH_POLICY` actions outperform deterministic heuristics.
- [ ] Measure whether compression saves tokens while increasing hidden reacquisition/interaction cost.

Adoption requires measured quality preservation.

## v0.7 — Offline policy evolution experiments

Goal: improve the Skill from benchmark evidence without allowing uncontrolled production self-modification.

Candidate loop:

```text
benchmark traces
  → failure clustering
  → candidate description/policy mutations
  → blinded holdout + real-agent A/B
  → human review
  → versioned promotion
```

- [ ] Test failure-driven manifest/activation description rewrites.
- [ ] Test offline mutation of policy boundaries.
- [ ] Keep production Skill versions deterministic and reproducible.
- [ ] Require blinded holdout improvement before promotion.

## Stable 1.0 gate

ACE-S should not be called stable until all of the following hold:

1. activation behavior is reliable across simple and complex tasks;
2. the system does not need to preload every specialist policy to achieve that reliability;
3. wrong-first candidate routing is recoverable at bounded cost;
4. exact/provenance-sensitive tasks show no material fidelity regression;
5. at least one reproducible real-agent benchmark shows a meaningful benefit;
6. failure modes, no-uplift cases, and limitations are documented;
7. installation and use are tested by users other than the original author;
8. benchmark claims can be regenerated from public raw results and scoring code.

## Non-goals

ACE-S does not plan to become:

- a vector database;
- a proprietary memory server;
- a mandatory agent framework;
- a model-routing gateway;
- a benchmark leaderboard optimized at the expense of correctness;
- a giant classifier that loads every architecture/policy to decide which one to use;
- a system that assumes more context is always better.

The project should remain portable: a policy/controller that can sit above different context backends.
