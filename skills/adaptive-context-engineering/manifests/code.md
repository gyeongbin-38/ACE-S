# CODE Manifest

## Use when

The answer depends on repository structure that is not already fully present: symbols, implementations, callers, tests, commits, dependencies, or change impact.

## Do not use when

- the complete relevant code is already supplied and the task can be solved from it;
- the task only rewrites or explains supplied code without repository lookup;
- external evidence, not repository structure, dominates the next step.

## Entry action

Prefer the narrowest structural locator available: exact file/path/symbol, then local dependencies/tests, then broader search.

Typical entry fidelity: `INDEX` or `EXTRACT`.

## Open next

If this manifest fits, read only `references/coding.md`.

Lazy additions:

- load `manifests/evidence.md` only if exact contracts/source truth become material;
- load `manifests/temporal.md` only if branch/version/release freshness can change the answer;
- load `manifests/retention.md` only if later implementation/handoff needs state gathered now;
- load `manifests/tools.md` only if the code-inspection capability itself is unknown.
