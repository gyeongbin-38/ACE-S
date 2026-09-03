# Performance and Scale Protocol

Use only when workload/performance requirements can change architecture.

## 1. Convert "fast" and "scalable" into a workload scenario

Specify when material:
- operation/flow;
- arrival/concurrency shape;
- payload/state size;
- read/write ratio;
- burst duration;
- latency/throughput bound;
- availability/degradation expectation.

Do not optimize for an unspecified future scale.

## 2. Trace the critical path

Identify the latency/throughput path and assign rough budgets only where evidence is useful:
- compute
- network hops
- storage
- serialization
- queues
- external dependencies
- lock/contention points

A new service boundary adds network/serialization/failure cost. It is not a scaling mechanism by itself.

## 3. Find the limiting resource

Before splitting architecture, ask what actually saturates first:
- CPU/GPU
- memory
- connection/thread/event-loop capacity
- storage IOPS/locks
- network bandwidth
- external quota
- queue consumer throughput

Prefer measurement or a bounded load model over pattern guessing.

## 4. Independent scaling must be real

A component deserves independent scale pressure when:
- its workload grows differently from neighbors;
- it can scale without requiring coordinated scaling of the same bottleneck;
- the interface/state semantics permit independent instances/partitioning;
- the operating benefit exceeds the distributed boundary cost.

If both sides still depend on one dominant state/resource bottleneck, service separation may add complexity without scale isolation.

## 5. Scaling mechanisms are conditional

Possible mechanisms include vertical scale, concurrency tuning, batching, caching, partitioning, replication, async buffering, precomputation, or boundary separation. Choose only after identifying the limiting path and state semantics.

Any cache/replica/partitioning choice that changes state correctness should activate STATE.

## 6. Tail behavior and overload

When p95/p99 or overload matters, test queueing/saturation behavior rather than average latency only. State the load-shedding/backpressure/degraded-mode contract if applicable and activate FAILURE when it becomes architecture-significant.

## 7. Fitness checks

Examples:
- representative load test with fixed workload profile;
- p95/p99 SLO gate;
- throughput/saturation curve;
- resource budget alert;
- cache hit/staleness guard;
- partition skew test;
- overload/backpressure test.

A performance claim without a reproducible workload definition is unresolved.
