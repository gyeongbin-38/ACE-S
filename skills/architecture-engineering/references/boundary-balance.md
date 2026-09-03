# Boundary Balance Protocol

A boundary is not justified merely because a separation force exists. Architecture must also account for the forces pulling the two sides together.

This protocol uses two opposing sets of evidence:

- **separation pressure** — reasons the sides should be farther apart;
- **cohesion pressure** — reasons the sides should remain close.

Expected change amplifies the cost of getting that balance wrong.

## 1. Separation pressure

Examples:
- materially different trust or privilege domains;
- failure/blast-radius isolation;
- independent scaling or performance profile;
- independent deployment/runtime constraint;
- platform or data-residency requirement;
- genuinely independent ownership/release cadence;
- strong provider/technology isolation requirement.

Some separation pressures can be non-negotiable, especially trust, regulatory, or runtime-isolation constraints.

## 2. Cohesion pressure

Examples:
- one business invariant spans both sides;
- immediate transactional consistency is required across the proposed boundary;
- changes usually require both sides to move together;
- a rich shared domain model would cross the boundary;
- the interaction is chatty or latency-sensitive;
- one side cannot make a meaningful decision without private knowledge from the other;
- lifecycle/recovery semantics are tightly coupled.

High cohesion pressure does not forbid a boundary. It means a distant boundary must include an explicit mechanism that reduces or manages the pressure.

## 3. Change likelihood

Classify the relationship, not just each component:
- `HIGH` — requirements or implementation are expected to evolve frequently;
- `MEDIUM` — periodic meaningful change;
- `LOW` — stable, standardized, or replaceable behind a mature contract;
- `UNKNOWN` — preserve as uncertainty and measure before making a high-lock-in split.

Historical co-change can support this judgment for existing systems, but observed history is evidence, not ground truth: poor existing boundaries can themselves create co-change.

## 4. Boundary distance

Use an ordinal distance sufficient for the decision:
- `INTERNAL` — same implementation unit;
- `MODULE` — explicit module/package boundary, same deployable/process;
- `PROCESS` — separate runtime/process;
- `SERVICE` — independently deployable network boundary;
- `SYSTEM` — separately governed external system/provider.

Higher distance increases coordination, failure, compatibility, and observability costs.

## 5. Balance rule

Do not use a universal numeric formula.

Instead apply these gates:

1. If there is a non-negotiable separation constraint, preserve the required distance and explicitly mitigate every material cohesion pressure.
2. If cohesion pressure is high and separation pressure is weak, prefer lower distance.
3. If separation pressure is high and cohesion pressure is weak, a stronger boundary is plausible.
4. If both are high, the boundary is a **decision hotspot**. It requires an explicit mechanism, scenario attack, and reversal/merge condition.
5. If both are weak, do not invent a distributed boundary for aesthetics; use the simplest local structure that preserves clarity.
6. High expected change raises the severity of any unresolved imbalance.
7. `UNKNOWN` material pressure blocks a high-lock-in decision unless a bounded-risk migration path exists.

## 6. Cohesion mitigation patterns

When separation is required despite cohesion pressure, make the mechanism explicit. Depending on the domain, examples include:
- move an invariant so one side becomes the authoritative decision owner;
- expose a narrow command/query contract instead of a shared model;
- duplicate immutable reference data with versioning rather than share writable storage;
- introduce compatibility windows for independently deployed versions;
- use a well-defined asynchronous consistency protocol only where the business invariant permits it;
- co-locate latency-sensitive control while separating slower administrative concerns;
- keep one transaction boundary and split only read/compute paths that do not own the invariant.

Do not call generic messaging, caching, or eventual consistency a mitigation unless it actually satisfies the ASR.

## 7. Boundary Decision Certificate

For consequential boundaries record:

```text
boundary_id
between
chosen_distance
separation_pressure[]
cohesion_pressure[]
change_likelihood
non_negotiable_constraint | null
cohesion_mitigation[]
interface_contract
state/consistency effect
failure effect
cost introduced
scenario evidence
merge/reversal condition
```

The certificate is unresolved when a material pressure is `UNKNOWN`, a high-distance boundary conflicts with material cohesion pressure without mitigation, or the stated contract cannot explain how the relevant invariant is preserved.

## 8. Existing-system evidence

When redesigning existing code, gather the minimum evidence needed to test the proposed balance:
- dependency/call edges;
- state/storage access;
- deploy/runtime topology;
- ownership if available;
- selected change/co-change history;
- contracts and tests at the seam.

Documentation is design intent. Code, deployment, configuration, and tests are observed reality. If they disagree, preserve the drift explicitly rather than silently choosing one.

## 9. Design implication

The goal is not maximum decoupling. The goal is **the cheapest distance at which architecture pressures are balanced while all ASRs and hard constraints remain satisfied**.
