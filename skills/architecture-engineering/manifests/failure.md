# FAILURE

Use when the next decision depends on partial failure, dependency outage, retry behavior, backpressure, saturation, degraded mode, recovery ownership, or blast radius.

Check first:
- what can fail independently?
- how is failure detected and bounded?
- what timeout/retry budget is safe?
- where does backpressure apply?
- what state makes retries unsafe?
- what is the recovery/degraded-mode contract?

Do not prescribe resilience patterns everywhere; load only for material failure paths.

If material, read `../references/failure-resilience.md`.
