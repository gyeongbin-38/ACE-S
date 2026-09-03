# STATE

Use when correctness depends on mutable state ownership, transactions, consistency, ordering, idempotency, replication, lifecycle, or recovery.

Check first:
- what is the authoritative state?
- who may write it?
- what invariant/consistency is actually required?
- what happens on duplicate/reordered/partial operations?
- how is state rebuilt or recovered?

Do not load merely because a database exists.

If material, read `../references/state-consistency.md`.
