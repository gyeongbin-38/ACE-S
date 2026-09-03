# BCS v0.4 Experiment Decision Log

Status: experimental branch decision record. This file records both positive and negative synthetic evidence so later architecture edits do not silently retain only favorable results.

## Decision rule

**Quality First, Efficiency Second. Prove before Predict.**

An optimization is eligible for the BCS candidate architecture only when its claimed efficiency benefit survives the benchmark's predeclared quality/evidence gate. Development-only wins are hypotheses, not adoption evidence.

## Strong candidates

### Structural dominance pruning — KEEP

Rule: remove action A only when another action B is no more expensive and B's observation partition provably refines A on the current state.

Sealed synthetic OOD:
- exact optimum preservation: `100%`
- initial candidate reduction: `50.626%`

Boundary: structural/typed metadata only; semantic similarity is not a proof.

### Cost-floor pruning with abstention — KEEP

Rule: if a feasible complete-plan upper bound exists, prune an action whose unavoidable immediate/lower-bound cost already exceeds that upper bound. If no valid bound exists, abstain.

Sealed synthetic OOD:
- exact optimum preservation: `100%`
- structural dominance candidate reduction: `8.405%`
- combined structural + cost-floor reduction: `30.001%`
- incremental reduction on structural frontier: `24.213%`

A nominal no-bound fixture was found to accidentally contain one-step complete actions. A strict repaired negative control then verified:
- 300 worlds
- one-step complete actions: `0%`
- reported upper-bound availability: `0%`
- exact optimum preservation: `100%`

Interpretation: keep the algorithm; fix the benchmark fixture. Do not erase the original fixture flaw from history.

### Typed Evidence Certificate — KEEP AS STRONG CANDIDATE

Frozen conservative contract:
- structured + explicitly certificate-capable only,
- exact typed observed outcome,
- source/provenance reference,
- worker-visible state update equivalent to full structured exposure,
- semantic evidence never certificate-compressed,
- certificate payload cost fixed to `75%` of full structured exposure,
- validation cost fixed to `15%` of acquisition cost.

Post-freeze sealed OOD:
- 270 worlds
- all worlds solvable under both policies
- no semantic certificate capability
- effective cost reduction remained positive at every tested call penalty:
  - penalty `0.5`: `6.417%`
  - penalty `1.0`: `5.296%`
  - penalty `2.0`: `3.946%`
  - penalty `4.0`: `2.500%`
- intrinsic context-cost reduction also positive at all penalties
- all predeclared gates passed

Boundary: synthetic typed-tool economics. Real use requires schema validation, provenance-preserving serialization, and measured token/RPC/latency cost.

### Exact frontier + typed certificate composition — KEEP

Frozen composition rule:
1. apply legal typed-certificate cost semantics only to structured certificate-capable evidence;
2. apply structural dominance and valid cost-floor pruning to the resulting action frontier;
3. require the pruned exact optimum to equal the unpruned certificate-aware exact optimum.

Development interaction test:
- 360 worlds
- exact optimum preservation: `100%`
- mean candidate reduction: `45.618%`
- full-exposure total-cost reduction: `8.808%`

Post-freeze sealed OOD used six new families and seed `386117509`:
- 420 worlds
- exact optimum preservation: `100%`
- mean candidate reduction: `58.849%`
- mean total-cost reduction vs full exposure: `8.081%`
- no semantic certificate capability
- all worlds solved
- all predeclared gates passed

Per-family sealed total-cost reduction:
- `cheap_semantic_complete`: `0.111%`
- `expensive_typed_complete`: `6.153%`
- `mixed_wide_cost`: `9.425%`
- `redundant_typed_and_semantic`: `8.618%`
- `semantic_heavy_low_cert`: `1.638%`
- `typed_high_payload`: `14.782%`

Interpretation: the two mechanisms operate on different cost axes. Typed certificates reduce legal execution/exposure cost; proof pruning reduces the candidate search frontier while preserving the same certificate-aware optimum. Do not add their percentages as if they were independent end-to-end savings.

Boundary: post-freeze synthetic finite-decision OOD, not frontier-model answer quality or measured latency.

### Receding-horizon lifecycle retention — KEEP AS CANDIDATE

Frozen one-step rollout over `RAW / ABSTRACT / DROP` versus fixed retention heuristic.

Sealed synthetic lifecycle OOD:
- base mean optimal ratio: `1.12895`
- rollout mean optimal ratio: `1.05894`
- P90: `1.37861 → 1.04149`
- within +5% of optimum: `78.99% → 90.64%`
- within +10%: `81.95% → 92.22%`
- rollout beats/ties base: `100%`

Boundary: lifecycle economics with generator-level probabilities, not real-agent answer quality.

## Rejected or deferred

### Plain acquisition/exposure separation — REJECT AS DEFAULT

Corrected controller-state / worker-state benchmark:
- total cost: `-4.128%`
- worker exposure: `-5.299%`
- acquisition cost: `-1.593%`
- tool calls: `+19.111%`

Conclusion: merely hiding controller-readable data from the worker is not sufficient. Use an exact typed certificate or expose required evidence normally.

### Generic pair batching — REJECT AS ARCHITECTURE FEATURE

220-world exact-DP benchmark:
- total cost improvement: `0%`
- tool-call improvement: `0%`
- worker-exposure improvement: `0%`

Conclusion: current controller often needs only one structured action, so generic pair bundles do not enter the optimal frontier. Keep batching as a backend-specific capability when a real API provides shared call overhead.

### Adaptive K / task-shape budget heuristics — REJECT

Aggressive development search found large sample savings but unacceptable environment degradation. Example:
- rollout-sample reduction: `71.6%`
- environment cost: `+3.879%`

Conclusion: not Quality-First.

### Selective retention depth from lifecycle topology — REJECT

v3 development looked strong:
- depth3 rate: `39.111%`
- captured depth3 gain: `95.432%`
- mean cost reduction vs depth1: `8.139%`

Post-freeze OOD collapsed:
- depth3 rate: `2.5%`
- captured depth3 gain: `7.999%`
- mean reduction vs depth1: `0.243%`

Conclusion: task/lifecycle shape is not a reliable general depth selector.

### Pilot action-agreement adaptive compute — REJECT

Post-freeze OOD:
- rollout-sample reduction: `39.25%`
- mean environment cost: `+2.941%`
- P90 per-world delta: `+16.741%`
- P95: `+28.118%`
- max: `+76.43%`

Conclusion: pilot agreement does not control rare tail error.

### Sequential racing v2 — REJECT

Development quality gates based on mean/P90 looked acceptable:
- sample reduction: `40.538%`
- mean environment change: `+0.937%`
- worlds within +1%: `94.722%`

But max single-world degradation was `52.811%`.

Lesson: mean/P90 gates can hide catastrophic tail failures.

### Sequential racing v3 with explicit tail gates — REJECT AS DEFAULT

Fresh development after introducing max/CVaR gates:
- sample reduction: `8.527%`
- mean environment change: `-0.012%`
- P95: `0%`
- within +1%: `100%`
- max: `0%`
- CVaR95: `0%`

Post-freeze adversarial OOD:
- sample reduction: `7.912%`
- mean environment change: `+0.110%`
- P95: `0%`
- within +1%: `99.375%`
- CVaR95: `+2.163%`
- max single-world degradation: `+38.708%`

Predeclared max <=10% gate failed.

Conclusion: even conservative empirical racing still has a rare catastrophic miss.

### Family-wise risk-controlled racing calibration — NO CERTIFICATE / CLOSE CURRENT LINE

A stricter follow-up treated catastrophic failure as `adaptive environment cost > fixed-K8 cost × 1.10` and attempted to certify risk rather than tuning a heuristic threshold.

Predeclared calibration protocol:
- calibration worlds: `900`
- candidate policies: `48`
- target catastrophic risk: `<=1%`
- family-wise confidence: `95%`
- multiple-policy correction: Bonferroni
- risk bound: exact one-sided binomial upper bound

Result:
- certified policies: `0`
- a high-compute-saving candidate still had empirical catastrophic rate `3.22%`
- corrected upper bound: `5.46%`
- observed max degradation: `95.95%`
- controller decision: `retain_fixed_k8`

Conclusion: do not weaken the risk target or confidence level after seeing this result. The current empirical-racing family is closed as a default BCS optimization. Re-open adaptive early stopping only with a materially different certificate/model whose guarantee and shift assumptions are explicit.

## Measurement corrections

### Rollout samples are not expensive-model-call counts

A cache-accounting audit of 320 synthetic worlds found:
- mean rollout sample draws: `68.638`
- mean unique memoized base-value evaluations: `22.306`
- mean cache hits: `80.878`
- unique evaluations / sample draws: `32.713%`

Therefore do not make public claims such as "controller compute reduced by X%" from sample count alone.

Future reports should separate:
1. algorithmic sample draws,
2. unique/cache-aware value evaluations,
3. tool/RPC calls,
4. worker-visible token/byte exposure,
5. controller-only token/byte exposure,
6. certificate token/byte representation,
7. measured tool/model/wall-clock latency.

### Runtime trace contract now exists

The experimental branch now includes a real-runtime trace contract, validator, summarizer, positive structured-certificate fixture, negative semantic-certificate fixture, and CI. The validator rejects semantic certificate compression and requires provenance-preserving exact typed certificates.

This validates instrumentation semantics only. It is not itself an end-to-end model benchmark.

## Architecture consequence

Current evidence supports the following default ordering:

```text
SUFFICIENT?
  ↓ no
hard feasibility
  ↓
structural dominance
  ↓
valid upper-bound / cost-floor pruning
  ↓
context action frontier
  ↓
conservative uncertain evaluation
  ↓
execute one action
  ↓
typed certificate if exact-equivalent and legal
  otherwise selected evidence exposure
  ↓
update controller + worker states
  ↓
lifecycle decision
  ↓
STOP / REPLAN
```

Adaptive early stopping is disabled by default in the current BCS candidate. The attempted family-wise risk calibration certified no empirical racing policy at the predeclared 1% catastrophic-risk target. Fixed/conservative frontier evaluation remains the fallback.

## Public claim boundary

These are synthetic controller and lifecycle experiments plus instrumentation-contract tests. They are useful for falsifying controller designs, validating bounded mechanics, and preventing misleading metric accounting, but they do not establish frontier-model answer-quality improvement or measured Web GPT/Codex latency savings. Those require an external real-task benchmark with final-quality scoring and runtime measurement.
