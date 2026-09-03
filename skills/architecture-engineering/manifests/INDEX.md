# Architecture Concern Index

Use this index after the kernel has framed the current architecture-changing question. Load **one primary concern first**. Keep at most one backup when the hotspot genuinely spans two concerns.

| Concern | Load when the next decision mainly depends on | Entry reference |
|---|---|---|
| `BOUNDARY` | split/merge, module/service distance, coupling/change locality | `boundary.md` |
| `STATE` | ownership, transactions, consistency, ordering, replication, recovery | `state.md` |
| `TRUST` | identity, authorization, tenant isolation, secrets, privilege boundaries | `trust.md` |
| `FAILURE` | dependency outage, retries, backpressure, blast radius, degraded mode | `failure.md` |
| `PERFORMANCE` | latency, throughput, scale shape, hotspots, resource contention | `performance.md` |
| `EVOLUTION` | deploy independence, compatibility, migration, schema/protocol evolution, reversibility | `evolution.md` |
| `GENERIC` | no concern clearly dominates yet; locate the next architecture-changing fact | `generic.md` |

Do not classify every concern at task start.

Typical late specialization:

```text
ASR says tenant data must be isolated
  -> TRUST manifest
  -> isolation implies process boundary
  -> BOUNDARY manifest
  -> shared state appears across the proposed split
  -> STATE manifest
```

Load the next concern only because the current reasoning exposes a material dependency, not for completeness.
