# Architecture Evaluation Protocol

Use this only after a candidate architecture exists or when reviewing an existing design.

## 1. Gate before scoring

A candidate is ineligible if any critical condition below is unresolved:
- violated hard constraint;
- critical ASR has no mechanism;
- critical mutable state has ambiguous ownership;
- trust boundary lacks enforcement;
- critical failure path lacks containment/recovery;
- required migration path is impossible under stated constraints.

Do not let a high aggregate score compensate for a hard failure.

## 2. Relational completeness

Architecture quality is primarily about relationships, not the number of boxes.

For every critical flow verify:
- entry point and caller;
- interface/contract;
- state read/write owner;
- consistency semantics;
- authorization/enforcement point;
- failure propagation and retry behavior;
- observability point;
- exit/result path.

Flag any critical flow with an implicit hop as `RELATION_GAP`.

## 3. Boundary justification

For each boundary count the material forces that justify it.

Possible forces:
- change coupling separation
- state/consistency separation
- trust separation
- failure isolation
- scale/performance separation
- deployment/runtime separation
- ownership separation

Flag:
- `BOUNDARY_WITHOUT_FORCE`: no material force.
- `DISTRIBUTED_WEAK_BOUNDARY`: network/process boundary with only a weak convenience rationale.
- `BOUNDARY_CONFLICT`: chosen boundary fights a stronger coupling/consistency force.

## 4. State model

Every mutable state category should have one authoritative owner or an explicit multi-writer protocol.

Evaluate:
- source of truth
- writer set
- consistency level
- idempotency/deduplication
- ordering requirement
- lifecycle and retention
- recovery/rebuild path

Flag implicit shared state and undefined reconciliation.

## 5. Failure model

For each external dependency and deployable/runtime unit identify:
- timeout
- retry policy and budget
- backpressure
- circuit/open-state behavior if relevant
- idempotency
- degraded mode
- recovery ownership
- blast radius

Do not demand every mechanism everywhere; demand an explicit answer where failure is material.

## 6. Permission and trust model

For each trust boundary identify:
- principal / identity
- credential or capability
- authorization decision point
- least-privilege scope
- secret ownership and rotation
- tenant/resource isolation
- audit trail when required

## 7. Quality-attribute scenarios

Use measurable scenarios where possible. Record:
- stimulus
- environment
- artifact/path
- expected response
- response measure
- sensitivity points
- tradeoff points

The scenario should be able to falsify the architecture claim.

## 8. Complexity ledger

Architecture mechanisms incur recurring cost. Track at least:
- deployable units
- network boundaries on critical flows
- independently persisted state stores
- asynchronous queues/streams
- cross-boundary transactions/sagas
- operational control planes
- bespoke infrastructure
- coordinated-release edges

Complexity is not automatically bad. Flag complexity whose driver is missing.

## 9. Reversibility ledger

Classify major decisions:
- `REVERSIBLE`: local/configurable, cheap to change.
- `MIGRATABLE`: expensive but has a staged migration path.
- `IRREVERSIBLE_OR_HIGH_LOCKIN`: data/protocol/topology choice with high switching cost.

Higher-lock-in choices need stronger evidence and explicit kill/reversal conditions.

## 10. Fitness functions

Translate important architectural claims into checks where feasible.

Examples:
- dependency direction lint
- forbidden cross-module imports
- API/schema compatibility tests
- max p99 latency SLO
- chaos/failure recovery test
- tenant-isolation test
- idempotency replay test
- queue-lag/backpressure alarm
- database migration compatibility test
- deployment independence check
- cost budget alert

A claim without a feasible automated check may still be valid, but should have an inspectable review procedure.

## 11. Pareto report

For each surviving candidate report qualitative or measured values for:
- functional/consistency correctness
- performance
- availability/recovery
- security/isolation
- modifiability
- deployability
- operability
- cost
- complexity
- migration risk
- irreversible commitment count

Do not emit a single winner score unless the stakeholder has explicitly provided utility weights. Otherwise identify:
- dominated candidates;
- Pareto frontier;
- decision that would change the winner;
- evidence needed to resolve remaining uncertainty.

## 12. Architecture quality summary

A review should end with:
- hard-gate result;
- ASRs covered/uncovered;
- relation gaps;
- unjustified boundaries;
- state/trust/failure ambiguities;
- highest sensitivity points;
- major tradeoffs;
- unresolved blocking/risk-bearing unknowns;
- fitness functions;
- recommended next architecture-changing question.
