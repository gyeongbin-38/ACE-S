---
name: architecture-engineering
description: Use for non-trivial software/system architecture design, architecture review, boundary design, decomposition, state/permission/failure modeling, or architecture decision work. Do not jump directly from requirements to components. First extract architecturally significant requirements and hard constraints, then synthesize only the boundaries justified by evidence, attack candidates with quality-attribute scenarios, and preserve explicit decision provenance. Load detailed synthesis/evaluation references progressively rather than preloading the whole method.
license: MIT
metadata:
  version: "0.1.0-experimental"
  methodology: "evidence-constrained proof-carrying architecture synthesis"
---

# Architecture Engineering

Design architecture as a **search over decisions under constraints**, not as diagram generation.

## Kernel

1. **Select the work mode.** Distinguish new-system design, redesign of an existing system, architecture review, and conformance verification. For redesign/review, treat docs and ADRs as intent until selected code/deploy/config/test evidence confirms reality.
2. **Frame before designing.** Extract the system goal, actors, hard constraints, architecturally significant requirements (ASRs), unknowns, and evidence already available.
3. **Do not invent boundaries from nouns.** A module/service/process/data boundary must be justified by architecture pressure, and any material pressure pulling the sides together must also be handled.
4. **Keep commitments reversible.** Defer technology, topology, distribution, and persistence choices that are not yet forced by an ASR or constraint.
5. **Generate alternatives only at real decision points.** Do not create arbitrary whole-system variants. Branch where two or more materially different choices remain plausible.
6. **Evaluate scenarios, not vibes.** Attack each candidate using measurable quality-attribute scenarios and failure cases before selecting it.
7. **Hard constraints gate; tradeoffs rank.** Reject candidates that violate hard constraints. Compare survivors as a Pareto frontier rather than hiding tradeoffs in one weighted score.
8. **Record why.** Every irreversible or expensive decision should preserve drivers, rejected alternatives, consequences, evidence, confidence, and reversal conditions.
9. **Attach fitness checks.** Important architectural claims should become executable or inspectable checks when possible.
10. **Promote proof-carrying designs.** Before treating a consequential design as final, require typed proof obligations for its critical boundaries, state, trust, flows, ASRs, and high-lock-in decisions.

## Progressive loading

For substantial design work, read `references/synthesis-loop.md` first.

Read `references/evidence-acquisition.md` only when the design/review needs facts not already present, especially for an existing repository or deployed system. Retrieve evidence around the current architecture-changing question rather than broadly inventorying the system.

Read `references/boundary-balance.md` only when creating, splitting, merging, or reviewing a consequential module/process/service/system boundary.

Read `references/decision-frontier.md` only when multiple interacting architectural choices remain feasible and manual comparison is becoming unreliable.

Read `references/evaluation.md` only when candidate architectures exist or an existing architecture is being reviewed.

Read `references/proof-obligations.md` only when finalizing/recommending a consequential architecture, reviewing high-risk decisions, or when the user explicitly asks for a production-grade architecture contract.

Do not load all references for trivial architecture questions.

## Stop rule

Stop architecture exploration when:

- all hard constraints are satisfied;
- material ASRs are covered by explicit mechanisms;
- no unresolved scenario exposes a likely architecture-changing risk;
- remaining alternatives differ mainly in reversible implementation detail;
- every major irreversible commitment has rationale and a reversal condition;
- critical proof obligations are resolved or explicitly accepted as bounded risk.

If those conditions are not met, take the **narrowest architecture-changing question** next rather than expanding the entire design.

## Invariants

- Quality before elegance.
- Relational correctness before component completeness.
- State ownership must be explicit.
- Trust and failure boundaries must be explicit when material.
- Distribution is earned, never assumed.
- Separation pressure must be checked against cohesion pressure before increasing boundary distance.
- Complexity is a cost and must have a driver.
- Unknowns are first-class; never fabricate rationale or requirements.
- Existing project constraints and accepted decisions outrank generic best practices unless they create a demonstrated critical risk.
- More available repository context is not a reason to load it; architecture evidence expands only when it can change a decision or resolve an obligation.
