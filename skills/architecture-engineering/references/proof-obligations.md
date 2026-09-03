# Proof-Carrying Architecture Obligations

A production-significant architecture should carry the evidence needed to explain and falsify its major decisions.

This is not formal proof in the theorem-proving sense. A proof obligation is a typed requirement for evidence, mechanism, and verification before a consequential architecture claim is treated as resolved.

## 1. Boundary Certificate

Required for expensive boundaries, especially network/process/service separation.

```text
boundary_id
separates
material_forces
ASRs_supported
cost_introduced
failure_modes_introduced
interface_contract
migration_or_merge_path
kill_condition
evidence_refs
```

A boundary without a material force remains unresolved.

## 2. State Ownership Certificate

Required for critical mutable state.

```text
state_id
authoritative_owner OR multi_writer_protocol
writers
readers
consistency_model
ordering/idempotency rules
retention/lifecycle
recovery/rebuild path
schema evolution strategy
fitness_checks
evidence_refs
```

If two components believe they are authoritative writers without a reconciliation protocol, fail the obligation.

## 3. Trust Enforcement Certificate

Required at material trust boundaries.

```text
boundary_id
principals
credential/capability model
authorization decision point
least-privilege scope
secret owner/rotation
tenant/resource isolation
audit requirement
attack scenario
fitness_check
evidence_refs
```

A trust line on a diagram is not an enforcement mechanism.

## 4. Critical Flow Certificate

Required for business/security/reliability-critical flows.

```text
flow_id
ordered relation path
interfaces/protocols
state touched
consistency semantics
authorization points
timeout/retry/backpressure behavior
failure containment
observability points
SLO or response measure
fitness_checks
```

Any implicit critical hop is an unresolved `RELATION_GAP`.

## 5. ASR Satisfaction Certificate

Required for every critical ASR.

```text
asr_id
scenario
architecture mechanisms
sensitivity points
tradeoff points
failure condition
response measure
fitness_check
```

A named technology is not itself an ASR mechanism unless the causal relation is explicit.

## 6. High-Lock-In Decision Certificate

Required for choices classified as `MIGRATABLE` or `IRREVERSIBLE_OR_HIGH_LOCKIN`.

```text
decision_id
drivers
alternatives
why alternatives lost
accepted downside
migration/reversal path
kill_condition
leading indicators that kill condition is approaching
evidence_refs
```

The stronger the lock-in, the stronger the evidence requirement.

## 7. Unresolved obligations

Do not fabricate missing evidence. Preserve:

```text
status: UNRESOLVED
missing: ...
risk_if_wrong: ...
cheapest_disambiguating_check: ...
decision_blocked: true|false
```

An explicit unresolved obligation is higher quality than invented certainty.

## 8. Promotion rule

A candidate may be promoted as the recommended architecture only when:
- hard constraints pass;
- all critical obligations are `RESOLVED` or explicitly accepted as bounded risk;
- no unresolved obligation is likely to reverse a major boundary or state/trust decision;
- fitness checks exist for the highest-risk claims;
- the candidate remains non-dominated on the current quality-attribute frontier.

Otherwise return the candidate plus the next cheapest architecture-changing question instead of pretending the design is final.
