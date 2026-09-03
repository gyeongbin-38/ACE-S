# Counterfactual Architecture Re-synthesis

Use this reference only when a consequential design is near promotion, when a
critical ASR is suspected to drive major structure, or when causal sensitivity
of the architecture must be tested.

The purpose is not to generate speculative future architectures. It is to test
whether the current decision graph responds **causally and locally** to a small
architecture-changing requirement mutation.

## Procedure

1. Pick one high-sensitivity input:
   - critical ASR;
   - hard constraint;
   - blocking/risk-bearing unknown that is about to become resolved.
2. Make the smallest meaningful counterfactual mutation:
   - add/remove a constraint;
   - tighten/relax a quality bound;
   - change consistency/isolation/availability/scale/deployment requirement;
   - reverse one accepted assumption.
3. **Before re-designing**, predict which existing decisions, mechanisms, proof
   obligations, scenarios, and fitness checks should reopen from the current
   traceability graph.
4. Re-synthesize only that governed neighborhood. Do not reload or redraw the
   whole system unless the impact closure proves the change is global.
5. Compare the before/after Architecture State Graphs:
   - required mechanisms changed when the requirement demands it;
   - existing unrelated nodes stayed stable;
   - new nodes are traceably anchored to the changed intent/decision closure;
   - removed nodes belonged to the reopened closure;
   - required fitness/scenario/proof checks were rerun;
   - new high-lock-in commitments have explicit new drivers.
6. Record the result as a counterfactual sensitivity check, not as production
   evidence for the mutated requirement.

## Failure patterns

### Architecture-insensitive
A material requirement changes but no relevant decision/mechanism reopens.

Likely causes:
- requirement never had a real traceability path;
- architecture was generated from generic patterns rather than requirements;
- mechanism is implicit or undocumented.

### Architecture-chaotic
A local requirement mutation causes unrelated boundaries, technologies, or
components to change.

Likely causes:
- decisions are over-coupled;
- the design lacks stable ownership/contracts;
- the generator is re-creating the whole architecture instead of revising a
  governed decision neighborhood.

### Commitment inflation
The mutation adds distributed/high-lock-in structure that is not linked to the
changed requirement or a newly exposed risk.

Treat this as architecture invention until justified.

## Selection budget

Do not counterfactually mutate every requirement.

Default to 1–3 mutations chosen by:
1. architecture sensitivity / blast radius;
2. uncertainty;
3. irreversibility of the decisions they drive;
4. severity if the assumption is wrong.

More counterfactuals are useful only when they can still change the promoted
architecture.

## Tooling

When two typed Architecture State Graphs exist, use the deterministic
`architecture_delta.py` evaluator for locality/revalidation accounting.

Its passing result does **not** prove semantic correctness. It proves only that
the revision is traceably local and that required governance checks were
reopened.
