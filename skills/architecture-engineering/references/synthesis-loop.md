# Evidence-Constrained Architecture Synthesis Loop

This reference defines the full design loop. The objective is not to maximize diagram detail; it is to minimize architectural regret under explicit constraints.

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

### A4. Architecture forces
Track forces that may justify boundaries:
- change coupling / release cadence
- state ownership / consistency requirement
- trust / privilege boundary
- failure isolation / blast radius
- independent scale / performance profile
- independent deployment / runtime requirement
- organizational ownership

Do not convert a domain noun directly into a component. A boundary needs a force.

### A5. Unknowns
Classify unknowns:
- `BLOCKING`: architecture cannot be chosen safely without resolving it.
- `RISK_BEARING`: architecture can proceed if a mitigation/reversal path exists.
- `REVERSIBLE`: defer it.

Never fill unknowns with invented assumptions without labeling them.

## B. Establish the Minimum Architecture

Start with the least distributed structure that can satisfy the known requirements.

Default pressure is **cohesion**, not decomposition.

Create a boundary only when at least one material force requires it. Stronger boundaries should normally have multiple independent forces or one non-negotiable force such as security isolation.

For every proposed boundary record:

```text
boundary
  separates: A <-> B
  forces: [...]
  state owner: ...
  interface: ...
  failure behavior: ...
  trust relation: ...
  cost introduced: ...
  merge condition: ...
```

This prevents architecture from silently accumulating distributed-system costs.

## C. Branch Only at Decision Frontiers

Do not generate three arbitrary whole architectures.

Find **decision frontiers**: places where materially different choices remain plausible and could change quality outcomes.

Typical frontiers:
- synchronous vs asynchronous coordination
- shared transaction boundary vs eventual consistency
- modular-monolith boundary vs deployable service
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

## D. Compose Candidates

Compose only mutually compatible frontier choices into candidate architectures.

Every candidate must make these relations explicit:
- component/module ownership
- request/event/data flows
- state owner for every mutable datum
- transaction/consistency boundary
- trust boundary
- failure propagation path
- deployment/runtime boundary
- observability points for critical flows

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
- "Split service" kill condition: >80% of changes require coordinated releases across the boundary.
- "Use async event" kill condition: domain requires immediate cross-aggregate serializable consistency.

A candidate is stronger when its failure conditions are known, not when it claims universal suitability.

## G. Eliminate, Then Compare

### G1. Eliminate
Reject any candidate that:
- violates a hard constraint;
- leaves a critical ASR without a credible mechanism;
- has ambiguous ownership of critical mutable state;
- crosses a trust boundary without an enforcement point;
- has an unbounded critical failure path with no mitigation.

### G2. Pareto comparison
Compare remaining candidates across dimensions rather than collapsing everything into one score:
- correctness / consistency
- latency / throughput
- availability / recovery
- security / isolation
- modifiability
- deployment independence
- operability / observability
- cost
- implementation complexity
- migration risk
- irreversible commitments

A candidate is dominated if another candidate is no worse on all material dimensions and better on at least one.

## H. Prefer the Least-Regret Survivor

Among non-dominated candidates prefer the architecture that:
- satisfies current ASRs;
- introduces the fewest unjustified boundaries;
- minimizes irreversible commitments;
- retains clear migration paths for uncertain future requirements;
- has executable fitness checks for its most important claims.

Do not optimize for hypothetical scale without evidence.

## I. Commit Decisions, Not Just Diagrams

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

Diagrams describe the current structure; decision records preserve why the structure exists.

## J. Re-enter Incrementally

When requirements or evidence change, do not redesign everything.

Locate which ASR, force, decision frontier, or kill condition changed and reopen only the affected decision neighborhood.

Architecture should evolve as a graph of governed decisions, not as periodically rewritten prose.
