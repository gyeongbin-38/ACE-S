# GENERIC

Use when the task is architecture-significant but no single concern yet dominates the next decision.

Do not load a specialist reference immediately.

Identify the smallest architecture-changing uncertainty:
- missing hard constraint or ASR?
- unclear current implementation reality?
- ambiguous state owner?
- unknown trust/failure boundary?
- unclear split/merge pressure?
- interacting decision frontier?

Resolve one bounded uncertainty, then specialize only if a concern becomes material.

For existing systems, use `../references/evidence-acquisition.md` when another fact must be retrieved.
