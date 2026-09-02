# STATE Manifest

## Use when

The task depends on distinguishing controlling/current state from superseded, conflicting, duplicated, or historically bounded state.

## Do not use when

- a fixed historical version/date is already unambiguous;
- the task is simply about the latest value with no conflicting state to reconcile;
- source navigation is better handled first by a repository/document/research domain.

## Entry action

Identify the controlling state key: version, revision, commit, effective date, record identity, or source authority. Keep current and superseded values separate.

Typical entry fidelity: `INDEX` first; use `RAW` only when the controlling state must be proven exactly.

## Open next

If this manifest fits, read only `references/temporal.md`.

Lazy additions:

- load `manifests/evidence.md` when resolving the conflict requires exact source authority;
- load `manifests/temporal.md` when freshness/effective-time semantics themselves need explicit handling.
