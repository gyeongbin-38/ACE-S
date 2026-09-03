# Evolution, Deployment, and Migration Protocol

Use only when independent evolution, rollout, migration, or lock-in can change architecture.

## 1. Define the change that must be survivable

Examples:
- deploy one module/service without coordinating another;
- change a schema while old/new application versions coexist;
- change an event/API contract;
- migrate a datastore/provider;
- move a boundary without downtime;
- roll back a failed release.

Do not demand independent deployment merely as an architectural virtue.

## 2. Compatibility window

If versions can overlap, identify:
- producers/consumers that coexist;
- backward/forward compatibility requirement;
- schema/protocol fields that may be added/removed;
- rollout order;
- when old behavior/data can be removed.

A design that requires lockstep rollout has coordinated-change coupling even if components are deployed separately.

## 3. Migration as a state machine

For high-risk changes represent migration stages explicitly, for example:

`OLD → DUAL_COMPATIBLE → NEW_PRIMARY → OLD_REMOVED`

Each stage should say:
- allowed readers/writers;
- data synchronization/backfill status;
- rollback point;
- verification/fitness check.

Avoid big-bang migration when staged compatibility is feasible and materially reduces risk.

## 4. Reversibility ledger

Classify major choices:
- `REVERSIBLE` — local/configurable/cheap to change;
- `MIGRATABLE` — costly but has a staged path;
- `IRREVERSIBLE_OR_HIGH_LOCKIN` — data/protocol/provider/topology decision with high switching cost.

The higher the lock-in, the stronger the evidence, alternatives, and kill-condition requirement.

## 5. Abstraction only for demonstrated volatility

Do not introduce provider layers, plugin systems, generic buses, or abstraction frameworks solely because a dependency might change someday.

An abstraction is justified when:
- replacement/evolution is a real ASR or known volatility;
- the abstraction can hide the expected variation without leaking the provider model;
- its ongoing complexity is lower than the expected migration/coupling cost.

## 6. Deployment independence vs architecture independence

Separate deployables are not automatically independent. Check:
- shared writable state;
- coordinated schema changes;
- synchronous availability dependence;
- shared configuration/secrets;
- lockstep protocol changes;
- coordinated release frequency.

If these remain dominant, the architecture may be distributed but operationally coupled.

## 7. Fitness checks

Examples when applicable:
- backward/forward compatibility test;
- mixed-version integration test;
- expand/contract migration test;
- rollback drill;
- deploy-one-side-without-other test;
- provider replacement contract test;
- schema migration linter;
- no-coordinated-release architecture check.

The goal is safe evolution of the decision graph, not maximal abstraction.
