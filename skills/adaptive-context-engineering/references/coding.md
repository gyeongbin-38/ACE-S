# Coding / Repository Route

For repository work, prefer structure before global semantic search.

1. Resolve explicit path, symbol, error, endpoint, test, or changed file.
2. Build a small structural neighborhood: callers/callees, imports, dependencies, sibling tests, config, or changed-file blast radius.
3. Search semantically/lexically inside that neighborhood.
4. Expand one hop only if evidence is insufficient.
5. Read raw code for files that can affect the change.
6. Verify against tests, contracts, or call sites.

Avoid scanning the whole repository when a structural seed exists.
