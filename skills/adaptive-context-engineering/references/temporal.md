# Temporal / Conflicting State Route

Use when a fact may have changed or two records disagree.

1. Identify the entity/property being queried.
2. Find the latest applicable value and at least the immediately relevant prior value when history matters.
3. Preserve timestamps/version/order and provenance.
4. Prefer current valid state for present-tense questions.
5. Keep superseded evidence available for historical questions; do not silently merge old and new facts.
6. If the current state is uncertain, say so and retrieve the narrowest evidence that can resolve it.

Treat summaries as caches; verify changed requirements and disputed state against raw records.
