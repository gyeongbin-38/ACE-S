# Context Action Frontier (CAF)

Status: experimental ACE-S v0.4 design component.

## Purpose

Do not send every generated context action into an LLM scorer or rollout planner. First shrink the action set using constraints and relations the runtime can prove cheaply.

```text
Candidate Generator
  ↓
Hard Feasibility Filter
  ↓
Structural Dominance Pruner
  ↓
Context Action Frontier
  ↓
Optional Bundle Generator
  ↓
Probabilistic Value / Outcome Estimator
  ↓
Bounded Rollout Scheduler
```

## Hard feasibility filter

Remove actions that cannot satisfy hard task constraints or cannot execute in the current environment. Examples:

- exact evidence is required but the action cannot preserve/recover provenance;
- freshness is mandatory but the source is known stale;
- capability/tool is unavailable;
- action violates a hard budget or permission boundary;
- result is already known and unchanged.

A hard filter must be based on runtime facts or explicit contracts, not model confidence.

## Structural dominance

Given current epistemic state S, action B structurally dominates A when:

1. B's observations distinguish every pair of worlds that A can distinguish on S (B's partition refines A's); and
2. B's measured immediate cost is no greater than A's.

Then A can be removed from the frontier without worsening the exact finite-state optimum under the benchmark formulation.

Examples that may admit a structural certificate:

- duplicate cache/local result is identical to a costlier remote fetch;
- a cached exact extract is already present while a coarser remote summary would cost more;
- one batched/index action is contractually a superset of another action at no greater marginal cost;
- two capability calls are known equivalent and one is strictly cheaper.

Do not use semantic similarity alone as a structural certificate.

## Why this matters

ACE-S should spend probabilistic/model compute only where uncertainty remains. The controller stack becomes:

```text
DETERMINISTIC PLANE
  constraints
  measured costs
  cache state
  provenance
  structural refinement
       ↓
UNCERTAIN PLANE
  expected answer-change value
  outcome probabilities
  bounded rollout
```

This reduces the surface area where an LLM or learned estimator can make errors.

## Interaction with source × fidelity

Source and fidelity remain independent action parameters. Dominance can occur across fidelity levels.

For example, if an exact extract is already cached locally, `FETCH remote SUMMARY` can be dominated by `REUSE cached EXTRACT` when the latter is both cheaper and strictly more informative.

Therefore fidelity is not a mandatory ladder and the frontier is state-dependent.

## Interaction with retention

A retained/offloaded context item changes the future frontier. Cache, retained exact refs, and compact summaries are not passive storage; they change the measured acquisition/reacquisition costs of future actions.

## Open extension: acquisition versus exposure

Fetching context into the controller and exposing context to the worker are distinct actions with distinct costs. A future ACE-S runtime should maintain separate budgets for:

- acquisition/I/O: tool calls, remote latency, bytes, money, backend load;
- exposure/attention: worker input tokens, attention dilution, context pollution.

Controller-side metadata or search results may be acquired without automatically being exposed to the worker. Only evidence selected for answer/reasoning should consume the worker exposure budget.
