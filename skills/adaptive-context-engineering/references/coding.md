# Coding / Repository Route

For repository work, prefer **specific structure over broad semantic search**.

## Retrieval ladder

1. Resolve any explicit path, symbol, error, endpoint, test, changed file, or domain term.
2. Run the smallest lexical/symbol query likely to identify a useful seed.
3. If the query is over-constrained and returns nothing, **remove descriptive noise before broadening scope**.
4. Once a useful seed appears, switch from global search to a local structural neighborhood:
   - defining symbol / implementation;
   - imports and direct dependencies;
   - callers/callees when available;
   - sibling source ↔ test files;
   - package/module neighbors;
   - changed-file blast radius;
   - docs/changelog only when they expose an exact symbol/path/issue clue.
5. Search semantically/lexically **inside that neighborhood**.
6. Expand one hop only if the current evidence is insufficient.
7. Read raw code for files that can affect the change.
8. Verify against tests, contracts, call sites, or the changed behavior.

## Useful follow-up patterns

```text
relevant test → imported symbol → production implementation
changelog/issue → exact function/class → implementation
package seed → sibling file / dependency → target
verbose query → exact symbol → target
```

These patterns were repeatedly useful in the 21-task Popular Repo Replay.

## Stop condition

Stop expanding when the current context contains the implementation target plus the minimum tests/contracts/dependencies needed to reason about the requested change.

Avoid scanning the whole repository when a structural seed exists. Avoid repeating global semantic searches after a useful local seed has already been found.
