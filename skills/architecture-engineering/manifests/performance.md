# PERFORMANCE

Use when architecture boundaries/topology may change because of latency, throughput, concurrency, resource contention, workload shape, or independent scaling.

Check first:
- what workload and response measure matter?
- where is the critical path?
- what resource is likely to saturate first?
- is scaling pressure genuinely independent or just hypothetical?
- which mechanism can be measured before adding distribution?

Do not load merely because the system should be "fast" or "scalable".

If material, read `../references/performance-scale.md`.
