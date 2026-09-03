# Failure and Resilience Protocol

Use only when failure semantics can change the architecture.

## 1. Build a bounded failure graph

For the critical flow identify:
- failure-capable dependency/runtime boundaries;
- synchronous waiting edges;
- queue/buffer edges;
- mutable state touched;
- retrying actors;
- recovery owner.

Do not enumerate every possible fault. Focus on failures that can change correctness, availability, latency, or blast radius.

## 2. Timeouts before retries

A remote/dependency wait needs a bounded failure-detection contract when indefinite waiting can harm the ASR.

Retries must answer:
- what failure is retryable?
- who retries?
- how many/for how long?
- is the operation idempotent?
- what amplification occurs during a broad outage?

Independent retry loops across layers can multiply load. Prefer a clear retry budget and ownership.

## 3. Backpressure and saturation

For bursty/queued/high-concurrency flows identify:
- first saturating resource;
- admission/buffer limit;
- producer behavior when the consumer cannot keep up;
- shedding/degradation policy;
- queue age/lag signal;
- recovery after overload.

Unbounded queues move failure into latency/memory instead of removing it.

## 4. Failure containment

A stronger boundary is justified for failure isolation only when it actually bounds shared resources/state/lifecycles. Separate services that share one saturated datastore or one mandatory synchronous chain may still share a blast radius.

Record:
- what fails independently;
- what remains available;
- which state can become inconsistent;
- how isolation is verified.

## 5. Degraded modes

When partial function is valuable, define the degraded contract explicitly:
- what operations remain safe?
- what data may be stale?
- what writes are rejected/queued?
- how users/callers learn the state?
- how normal mode is restored/reconciled?

Do not invent graceful degradation if the domain requires fail-closed correctness.

## 6. Recovery

For material failures state:
- detection signal;
- owner/on-call component/team if relevant;
- automated vs manual recovery step;
- state reconciliation;
- replay/restart semantics;
- recovery time/point objective when required.

## 7. Fitness checks

Examples when applicable:
- dependency fault injection;
- timeout/retry budget test;
- duplicate side-effect test;
- queue saturation/backpressure load test;
- degraded-mode contract test;
- restart/recovery drill;
- blast-radius/tenant-isolation failure test.

Do not add circuit breakers, queues, replication, or bulkheads as decorations. Each mechanism must answer a specific failure scenario.
