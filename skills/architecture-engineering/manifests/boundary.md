# BOUNDARY

Use when the next architecture decision is about whether two responsibilities should be closer or farther apart.

Check first:
- what separation pressure requires distance?
- what cohesion pressure makes distance expensive?
- how likely is the relationship to change?
- what is the cheapest distance that still satisfies the ASRs/constraints?

Do not load for simple internal refactoring with no architecture-significant boundary effect.

If material, read `../references/boundary-balance.md`.
