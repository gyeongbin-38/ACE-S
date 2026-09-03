---
name: architecture-engineering
description: Use for non-trivial software/system architecture design, architecture review, boundary design, decomposition, state/permission/failure modeling, or architecture decision work. Do not jump directly from requirements to components. First extract architecturally significant requirements and hard constraints, then synthesize only the boundaries justified by evidence, attack candidates with quality-attribute scenarios, and preserve explicit decision provenance. Load detailed synthesis/evaluation references progressively rather than preloading the whole method.
license: MIT
metadata:
  version: "0.1.0-experimental"
  methodology: "evidence-constrained architecture synthesis"
---

# Architecture Engineering

Design architecture as a **search over decisions under constraints**, not as diagram generation.

## Kernel

1. **Frame before designing.** Extract the system goal, actors, hard constraints, architecturally significant requirements (ASRs), unknowns, and evidence already available.
2. **Do not invent boundaries from nouns.** A module/service/process/data boundary must be justified by a material boundary force: change coupling, state/consistency, trust, failure isolation, independent deployment/scale, or ownership.
3. **Keep commitments reversible.** Defer technology, topology, distribution, and persistence choices that are not yet forced by an ASR or constraint.
4. **Generate alternatives only at real decision points.** Do not create arbitrary whole-system variants. Branch where two or more materially different choices remain plausible.
5. **Evaluate scenarios, not vibes.** Attack each candidate using measurable quality-attribute scenarios and failure cases before selecting it.
6. **Hard constraints gate; tradeoffs rank.** Reject candidates that violate hard constraints. Compare survivors as a Pareto frontier rather than hiding tradeoffs in one weighted score.
7. **Record why.** Every irreversible or expensive decision should preserve drivers, rejected alternatives, consequences, evidence, confidence, and reversal conditions.
8. **Attach fitness checks.** Important architectural claims should become executable or inspectable checks when possible.

## Progressive loading

For substantial design work, read `references/synthesis-loop.md` first.

Read `references/evaluation.md` only when candidate architectures exist or an existing architecture is being reviewed.

Do not load both references for trivial architecture questions.

## Stop rule

Stop architecture exploration when:

- all hard constraints are satisfied;
- material ASRs are covered by explicit mechanisms;
- no unresolved scenario exposes a likely architecture-changing risk;
- remaining alternatives differ mainly in reversible implementation detail;
- every major irreversible commitment has rationale and a reversal condition.

If those conditions are not met, take the **narrowest architecture-changing question** next rather than expanding the entire design.

## Invariants

- Quality before elegance.
- Relational correctness before component completeness.
- State ownership must be explicit.
- Trust and failure boundaries must be explicit when material.
- Distribution is earned, never assumed.
- Complexity is a cost and must have a driver.
- Unknowns are first-class; never fabricate rationale or requirements.
- Existing project constraints and accepted decisions outrank generic best practices unless they create a demonstrated critical risk.
