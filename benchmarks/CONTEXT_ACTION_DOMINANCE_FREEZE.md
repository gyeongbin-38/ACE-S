# Context Action Dominance — Protocol Freeze

Frozen implementation commit: `c0493bfad47c17e4ae795e60373d978ee304e4e7`

The structural pruning rule is frozen before the sealed/OOD generator and seed are introduced.

Rule:

- Let action B dominate action A only when B's observation partition refines A's partition on the current epistemic state, and B has no higher measured immediate cost.
- Remove only structurally dominated actions before value estimation / rollout.
- Recompute dominance after observations narrow the epistemic state.
- Do not use semantic similarity or predicted information value as proof of dominance.

Sealed evaluation must test exact-optimal preservation and controller rollout-compute reduction on new generator families/seeds. No coefficient or rule changes may be made after viewing sealed scores.
