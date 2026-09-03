# Condition D — Proof-Carrying Synthesis

Design a software/system architecture for the supplied project requirements.

Use evidence-constrained synthesis and internally maintain a typed architecture
state linking requirements/ASRs/constraints to decisions, boundaries, flows,
state, risks, verification, and available evidence.

Controls:

1. Extract hard constraints, critical ASRs, architecture-changing unknowns, and
   existing evidence before committing structure.
2. Start from the least distributed architecture that satisfies known needs.
   Boundaries are earned by separation pressure and must account for cohesion
   pressure, especially shared invariants, transactions, and coordinated change.
3. Generate alternatives only at consequential decision frontiers. Eliminate
   hard violations first; retain non-dominated tradeoffs rather than inventing
   stakeholder utility weights.
4. For each critical mutable state, make authority/consistency/recovery explicit.
   For each material trust boundary, identify enforcement. For each critical flow,
   identify interaction contracts and material failure behavior.
5. Attack sensitive/high-lock-in choices with relevant quality scenarios and a
   realistic counterexample or reversal condition.
6. Do not promote a consequential choice unless its driver is traceable and a
   measurable fitness check or bounded verification exists. Keep unsupported
   architecture-changing facts as risks/unknowns instead of fabricating evidence.
7. Prefer a local, reversible response to uncertainty. Do not add distributed or
   high-lock-in structure without a traceable requirement/risk driver.
8. When additional information is needed, seek the narrowest fact capable of
   changing the current architecture decision; do not broaden context for
   awareness alone.

Return **only** JSON conforming exactly to `OUTPUT_CONTRACT.md`.

The final JSON must expose only the requested architecture artifact, not private
reasoning, internal state traces, hidden references, or benchmark condition.
