# RETENTION Manifest

## Load only when

Later workflow steps, handoffs, long-running exploration, or large recoverable outputs create a real keep/offload/compact decision.

## Do not load when

- the task is one-shot;
- no later step depends on the gathered state;
- all necessary context is already small and stable.

## Entry action

Identify future-critical constraints, decisions, evidence refs, and unresolved questions. Keep those; offload recoverable bulk.

## Open next

If this modifier is material, read only `references/plan-aware.md`.
