# Condition C — Evidence-Constrained Synthesis

Design a software/system architecture for the supplied project requirements.

Internally follow these controls:

1. Extract hard constraints, architecturally significant requirements, and
   architecture-changing unknowns before naming components.
2. Start from the least distributed architecture that can satisfy the known
   requirements.
3. Create module/process/service/data/trust boundaries only when a material
   separation pressure exists, and check pressure pulling the sides together
   before increasing boundary distance.
4. Branch only at real decision frontiers where materially different choices
   remain plausible; do not generate arbitrary whole-system variants.
5. Reject hard-constraint violations. Compare viable alternatives by explicit
   tradeoffs rather than inventing one weighted quality score.
6. Attack material choices with failure, consistency, security, deployment,
   change, and operability scenarios when those concerns are relevant.
7. Preserve unknowns rather than filling them with unsupported assumptions.

Return **only** JSON conforming exactly to `OUTPUT_CONTRACT.md`.

The final JSON must not include private reasoning or the benchmark condition.
