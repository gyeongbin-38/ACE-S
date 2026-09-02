# Typed Evidence Certificate v0.1 — Frozen Before Sealed OOD

Status: `FROZEN_BEFORE_SEALED_TEST`

Freeze source commit: `66580c36dba644c1612d76b7c356ef6801c43ddb`
Development scripts:
- `scripts/discover_evidence_certificate_bench.py`
- `scripts/discover_certificate_call_penalty.py`

## Frozen conservative contract

A certificate may replace full worker exposure only when ALL are true:

1. the action is explicitly typed and `certificate_capable`,
2. the controller has observed one exact typed outcome,
3. the certificate carries that exact outcome plus source/provenance reference,
4. worker-visible epistemic state after certificate application is identical to the state produced by full structured exposure,
5. semantic/free-text evidence is never certificate-compressed,
6. termination still requires both controller and worker decision sufficiency.

For the sealed economic test, use a conservative certificate serialization cost equal to `0.75 * full_exposure_cost`, plus validation cost equal to `0.15 * acquisition_cost`.

This is intentionally much less aggressive than the best development setting (0.10–0.25 payload fraction).

## Development evidence at freeze

260-world exact-DP sensitivity:

- at 0.75 certificate fraction:
  - total cost reduction: `10.305%`
  - worker exposure reduction: `11.076%`
  - tool-call change: `+20.087%`
- even at 1.00 certificate fraction:
  - total cost reduction: `4.554%`
  - worker exposure reduction: `6.033%`

120-world call-penalty sensitivity re-optimized both conditions under equal penalties:

- 0.75 certificate fraction retained positive effective savings at every tested per-call penalty from `0.25` through `4.0`.
- at call penalty `4.0`: effective cost reduction `3.248%`, tool-call change `+1.508%`.

## Sealed protocol

After this freeze commit, introduce a fresh seed and new action/evidence families not used in development. Do not change the certificate fraction, validation fraction, or legality contract after seeing sealed outcomes.

Predeclared sealed gates:

- exact worker-state equivalence by construction for every certificate application,
- positive effective cost saving at call penalties 0.5, 1.0, 2.0, and 4.0,
- positive worker-exposure saving,
- no certificate use on semantic evidence,
- all tested worlds remain decision-solvable under both policies.

Failure of any gate means Evidence Certificates remain experimental rather than an architecture-default optimization.

## Claim boundary

Synthetic typed-tool economics only. Real adoption requires typed schemas/adapters, provenance-preserving serialization, validation, and measured token/RPC/latency costs in the target runtime. This is not an end-to-end LLM answer-quality benchmark.
