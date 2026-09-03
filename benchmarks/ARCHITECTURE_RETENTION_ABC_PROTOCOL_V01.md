# Long-Horizon Architecture Retention A/B/C Protocol v0.1

Status: `PROTOCOL_FROZEN_BEFORE_MODEL_RUN`

Candidate architecture freeze: `78a4f9072ee91833eedf50d30a4f772969ad9ce7`
Fresh controller OOD result: `b0bb3112b2134a2aff3028010244e990232e3d1c`

## Question

Does the transactional typed hybrid reduce real model architecture forgetting and stale-state errors over long work sequences compared with normal context handling and current ACE-S-style progressive context?

## Conditions

Use the same model/version, reasoning level, tools, task, source commit, and budget.

### A — OFF / normal agent
- no ACE-S architecture-memory runtime;
- ordinary conversation/history/context behavior;
- no hidden canonical-state injection.

### B — current ACE-S progressive context
- current ACE-S selective policy/capsule behavior;
- existing retention/handoff mechanisms only;
- no transactional canonical architecture graph introduced by this experiment.

### C — transactional typed hybrid
- append-only event log;
- transactional branch/checkpoint state;
- typed canonical architecture graph;
- pinned hard-constraint/proof-obligation ledger;
- bounded worker projection with provenance pointers.

No condition receives ground-truth labels or task-specific hints unavailable to the others.

## Minimum task matrix

30 tasks, 5 tasks per stratum:

1. `constraint_drift` — hard constraints introduced early, queried/enforced after long distractor work;
2. `decision_supersession` — old architecture decision replaced by a new one;
3. `speculative_rollback` — plausible branch is explored then explicitly rejected;
4. `proof_obligation` — implementation must remain blocked until evidence/fitness condition is satisfied;
5. `ownership_ripple` — state/component ownership changes and later code/design choices must follow the new owner;
6. `compound_long_horizon` — combines correction, rollback, provenance, and cross-module dependency over 50+ steps.

At least one third of tasks must contain a highly plausible but invalid stale/speculative answer.

## Run length

Each task must contain enough intermediate activity to stress working memory:
- minimum 30 model-visible steps;
- target 50–100 steps;
- at least 3 unrelated/distractor subproblems;
- at least 2 architecture-state changes for non-control strata.

## Primary metrics

1. `verified_task_success`
2. `hard_constraint_adherence`
3. `current_decision_accuracy`
4. `stale_state_error_rate`
5. `aborted_branch_contamination_rate`
6. `proof_obligation_violation_rate`
7. `architecture_provenance_accuracy`
8. `handoff_loss_rate`

## Efficiency metrics

Record separately:
- input/output tokens;
- worker-visible architecture bytes/tokens;
- controller-only state bytes/tokens;
- tool calls;
- state retrievals/projections;
- latency.

Quality dominates efficiency.

## Error taxonomy

```text
FORGOT_HARD_CONSTRAINT
USED_SUPERSEDED_DECISION
ABORTED_BRANCH_CONTAMINATION
PROOF_OBLIGATION_BYPASS
WRONG_STATE_OWNER
PROVENANCE_BREAK
HANDOFF_LOSS
OVER_CONTEXT_DISTRACTION
OTHER
```

Every failed run gets at least one class.

## Predeclared decision rule

C is the preferred architecture only if:

```text
C verified_task_success >= max(A, B)
AND C hard_constraint_adherence >= max(A, B)
AND C aborted_branch_contamination_rate <= min(A, B)
AND C proof_obligation_violation_rate <= min(A, B)
AND C has no >10% relative regression in any task stratum
```

If quality is tied, choose the condition with lower worker-visible architecture context and lower latency.

## Repetition and ordering

- minimum 3 independent runs per task/condition when model stochasticity is non-zero;
- randomize A/B/C order per task;
- do not reuse a failed task for tuning and then count it again as held-out;
- publish raw model outputs before scoring;
- scorer is blind to condition when practical.

## Claim boundary

This protocol is the first direct test of model-level architecture retention. Existing controller mechanics, repo localization, retention economics, Suite A, and Luna Suite B results are supporting evidence but do not substitute for this A/B/C.