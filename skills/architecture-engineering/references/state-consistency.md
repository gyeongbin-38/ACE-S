# State and Consistency Protocol

Use only when mutable state semantics can change architecture.

## 1. Start from invariants, not storage products

For each material state category identify:
- business/system invariant;
- authoritative value;
- allowed writers;
- readers that make decisions from it;
- acceptable staleness;
- ordering requirement;
- lifecycle/retention;
- recovery source.

Do not choose a database, cache, queue, or replication topology before these are understood well enough to matter.

## 2. Prefer one authority by default

A single authoritative owner reduces ambiguity. Multiple writers are allowed only with an explicit protocol that explains:
- conflict detection/resolution;
- ordering/versioning;
- idempotency/deduplication;
- convergence or transaction semantics;
- failure/recovery behavior.

Shared writable storage across architecture boundaries is a strong coupling signal and must be deliberate.

## 3. Consistency is per invariant

Do not label the whole system "strong" or "eventual".

For each invariant ask:
- must two facts become visible atomically?
- can a user observe an intermediate state?
- what stale decision would be harmful?
- is compensation semantically valid, or would it violate the domain?
- what response-time/availability tradeoff is acceptable?

Use the weakest consistency that still preserves the actual invariant, not the weakest consistency that is easiest to scale.

## 4. Derived state

Caches, indexes, projections, replicas, search stores, and materialized views should declare:
- authoritative source;
- maximum acceptable staleness;
- invalidation/update mechanism;
- rebuild path;
- behavior when the derived copy disagrees or is unavailable.

Derived state must not silently become a second source of truth.

## 5. Cross-boundary workflows

If one workflow touches multiple authorities, choose semantics explicitly:
- one transaction boundary because the invariant demands it;
- command ownership with idempotent retries;
- asynchronous propagation where temporary divergence is allowed;
- compensation only when reversing/offsetting the domain action is actually valid.

Do not use messaging as a substitute for deciding the invariant.

## 6. Ordering and idempotency

For retryable/distributed operations identify:
- stable operation/event identity;
- duplicate behavior;
- required ordering scope (global, per aggregate/entity/key, none);
- replay behavior;
- side effects that cannot be repeated safely.

Avoid global ordering unless the invariant truly requires it.

## 7. Recovery is architecture

For authoritative state specify:
- backup/snapshot/log source;
- recovery point objective if material;
- recovery time objective if material;
- rebuild/reconciliation procedure;
- who owns recovery;
- consistency checks after recovery.

A durable store with no tested recovery path is an incomplete state architecture.

## 8. Evolution

State/schema evolution should define how mixed application/schema versions coexist when zero/low-downtime rollout matters. Prefer staged compatibility and explicit migration state over coordinated big-bang changes.

Load the EVOLUTION concern only when the migration/deployment decision is architecture-significant.

## 9. Fitness checks

Examples when applicable:
- invariant/property tests;
- idempotency replay tests;
- duplicate/reordering tests;
- schema compatibility tests;
- projection rebuild test;
- restore/recovery drill;
- stale-read tolerance test.

The check must correspond to the claimed state mechanism rather than simply asserting that a technology is present.
