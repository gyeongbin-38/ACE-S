# Evidence-Constrained Architecture Synthesis Loop

This reference defines the full design loop. The objective is not to maximize diagram detail; it is to minimize architectural regret under explicit constraints.

## 0. Select the work mode

Choose only enough mode information to determine the next evidence step:

- `NEW_DESIGN` — no existing implementation constrains the target.
- `REDESIGN` — an existing implementation exists and target architecture may differ.
- `REVIEW` — evaluate an existing architecture without assuming redesign.
- `CONFORMANCE` — compare an accepted target/decision set against observed implementation.

For `REDESIGN`, `REVIEW`, or `CONFORMANCE`, reconstruct a bounded view of observed reality before relying on architecture docs. Treat requirements, ADRs, and diagrams as **intent evidence**; treat selected code, deploy manifests, configuration, runtime topology, storage use, and tests as **observed implementation evidence**. Record drift instead of silently choosing one source as truth.

Do not inventory an entire repository by default. Read only evidence that can alter a material architecture decision.

## A. Build the Architecture Problem Graph

Represent only information that can change architecture.

### A1. System intent
- mission / user-visible outcome
- primary actors and external systems
- business-critical flows
- explicit non-goals

### A2. Hard constraints
Examples: required platform, regulatory boundary, offline operation, deployment environment, fixed integration, maximum cost, mandated language/runtime, data residency.

A hard constraint is binary: a candidate either satisfies it or is rejected.

### A3. Architecturally significant requirements (ASRs)
Convert vague qualities into scenarios when possible:

`source/stimulus → environment → affected artifact → expected response → measurable bound`

Examples:
- 10k concurrent websocket sessions → peak traffic → ingress/session subsystem → no data loss → p99 reconnect < 2 s.
- credential compromise → production → tenant data plane → isolate tenant blast radius → no cross-tenant read.
- schema evolution → rolling deployment → event consumers → mixed versions coexist → zero coordinated downtime.

Every critical ASR should eventually trace to an architecture mechanism and a fitness check or inspectable verification procedure.

### A4. Architecture pressures
For each candidate relationship track pressures that may push the sides apart or together.

**Separation pressure** can include:
- trust / privilege isolation
- failure / blast-radius isolation
- independent scale or performance profile
- independent deployment / runtime requirement
- regulatory or data-location constraint
- independent ownership / release cadence

**Cohesion pressure** can include:
- shared business invariant
- immediate transaction / consistency requirement
- frequent coordinated change
- rich shared domain knowledge
- chatty or latency-sensitive interaction
- tightly coupled lifecycle / recovery

Also track expected change as `HIGH | MEDIUM | LOW | UNKNOWN`.

Do not convert a domain noun directly into a component. A stronger boundary must explain both the pressure that requires distance and any pressure that makes distance expensive. Read `boundary-balance.md` only when this decision becomes material.

### A5. Unknowns
Classify unknowns:
- `BLOCKING`: architecture cannot be chosen safely without resolving it.
- `RISK_BEARING`: architecture can proceed if a mitigation/reversal path exists.
- `REVERSIBLE`: defer it.

Never fill unknowns with invented assumptions without labeling them.

## B. Establish the Minimum Architecture

Start with the least distributed structure that can satisfy the known requirements.

Default pressure is **cohesion**, not decomposition.

Increase boundary distance only when:
- a non-negotiable constraint requires it; or
- material separation pressure remains after accounting for cohesion pressure and the added coordination/failure cost.

When a distant boundary is required despite material cohesion pressure, record the explicit mitigation: move invariant ownership, narrow the contract, change consistency semantics only if the ASR permits it, provide compatibility windows, or otherwise explain how the pressure is managed.

For every consequential proposed boundary record:

```text
boundary
  separates: A <-> B
  chosen_distance: INTERNAL | MODULE | PROCESS | SERVICE | SYSTEM
  separation_pressure: [...]
  cohesion_pressure: [...]
  change_likelihood: HIGH | MEDIUM | LOW | UNKNOWN
  non_negotiable_constraint: ... | null
  cohesion_mitigation: [...]
  state/consistency effect: ...
  interface: ...
  failure behavior: ...
  trust relation: ...
  cost introduced: ...
  merge/reversal condition: ...
```

This prevents architecture from silently accumulating distributed-system costs.

## C. Branch Only at Decision Frontiers

Do not generate three arbitrary whole architectures.

Find **decision frontiers**: places where materially different choices remain plausible and could change quality outcomes.

Typical frontiers:
- synchronous vs asynchronous coordination
- shared transaction boundary vs eventual consistency
- modular boundary vs deployable service
- centralized vs partitioned state ownership
- push vs pull processing
- single-region vs multi-region state strategy
- build vs managed infrastructure

For each frontier generate a small option set, normally 2–3 choices.

An option must state:
- driver
- mechanism
- benefits
- new failure modes
- operational cost
- migration/reversal path
- evidence needed to promote it

When frontiers interact combinatorially, load `decision-frontier.md` and use deterministic feasibility/Pareto filtering rather than asking a model to mentally optimize the full combination space.

## D. Compose Candidates

Compose only mutually compatible frontier choices into candidate architectures.

Every candidate must make these relations explicit:
- component/module ownership
- request/event/data flows
- state owner for every mutable datum
- transaction/consistency boundary
- trust boundary and enforcement point
- failure propagation path
- deployment/runtime boundary
- observability points for critical flows
- trace from each critical ASR to the mechanism(s) intended to satisfy it

A candidate with many named components but missing relationships is incomplete.

## E. Attack the Candidates

Run scenario attacks before preference ranking.

Minimum attack families when material:
1. peak load / latency
2. dependency outage / partial failure
3. stale, duplicated, reordered, or conflicting data
4. privilege compromise / tenant escape / secret exposure
5. deployment and schema migration
6. retry storm / backpressure / queue saturation
7. recovery from lost process/node/zone/region
8. observability and incident localization
9. feature change that crosses current boundaries
10. cost/operability under expected scale
11. a plausible change that should stay local but currently crosses several boundaries

For each scenario record:

```text
scenario
  stimulus
  path through architecture
  expected mechanism
  sensitivity points
  tradeoffs
  failure if mechanism breaks
  measurable fitness check
```

## F. Search for Counterexamples

For each major claim ask:

> What realistic condition would make this architecture choice wrong?

Record a `kill_condition` for important choices.

Examples:
- "Keep one database" kill condition: independently scaling write hotspots create unacceptable lock/IO contention.
- "Split service" kill condition: most material feature changes require coordinated releases across the boundary.
- "Use async event" kill condition: the domain proves it needs immediate cross-owner serializable consistency.

Also run a **remove-one-boundary counterfactual** for expensive boundaries:

> If this boundary were reduced by one distance level, which hard constraint or ASR would fail?

If no material failure can be named, the stronger boundary is not yet justified.

A candidate is stronger when its failure conditions are known, not when it claims universal suitability.

## G. Eliminate, Then Compare

### G1. Eliminate
Reject any candidate that:
- violates a hard constraint;
- leaves a critical ASR without a credible mechanism;
- has ambiguous ownership of critical mutable state;
- crosses a trust boundary without an enforcement point;
- has an unbounded critical failure path with no mitigation;
- contains a high-distance boundary with unresolved material cohesion pressure;
- depends on an unknown that is both architecture-changing and high-lock-in without a bounded migration path.

### G2. Pareto comparison
Compare remaining candidates across dimensions rather than collapsing everything into one score:
- correctness / consistency
- latency / throughput
- availability / recovery
- security / isolation
- modifiability / change locality
- deployment independence
- operability / observability
- cost
- implementation complexity
- migration risk
- irreversible commitments

A candidate is dominated if another candidate is no worse on all material dimensions and better on at least one. `UNKNOWN` is not zero and must not create artificial dominance.

## H. Prefer the Least-Regret Survivor

Among non-dominated candidates prefer the architecture that:
- satisfies current ASRs;
- introduces the fewest unjustified boundaries;
- minimizes irreversible commitments;
- retains clear migration paths for uncertain future requirements;
- has executable fitness checks for its most important claims;
- keeps high-cohesion relationships at the lowest practical distance unless a stronger constraint requires separation.

Do not optimize for hypothetical scale without evidence.

If several non-dominated candidates remain and stakeholder utility weights are absent, return the frontier and the next measurement/decision that could change it. Do not invent a mathematically optimal winner.

## I. Promote a Proof-Carrying Architecture

Before calling a consequential candidate final, load `proof-obligations.md` and attach typed obligations for critical boundaries, mutable state, trust enforcement, critical flows, critical ASRs, and high-lock-in decisions.

Missing evidence remains `UNRESOLVED`; do not fabricate rationale to complete the artifact.

## J. Commit Decisions, Not Just Diagrams

For each significant decision preserve:
- context / driver
- alternatives considered
- chosen option
- evidence
- accepted downsides
- sensitivity points
- kill/reversal condition
- affected modules/interfaces
- fitness functions
- unresolved risks

Maintain traceability:

`requirement / ASR → decision → architecture mechanism → relation/component/state → fitness check → observed implementation evidence`

Diagrams describe the current structure; decision records preserve why the structure exists.

## K. Re-enter Incrementally

When requirements or evidence change, do not redesign everything.

Locate which ASR, pressure, decision frontier, proof obligation, or kill condition changed and reopen only the affected decision neighborhood.

Architecture should evolve as a graph of governed decisions, not as periodically rewritten prose.
