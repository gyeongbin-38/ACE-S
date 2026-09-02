# Plan-Aware Route

Context value depends on future workflow steps, not only the current prompt.

1. Write the remaining steps or decision horizon.
2. For each context item, ask whether a future step is likely to need it.
3. Retain durable constraints, intermediate results, unresolved questions, and reusable evidence.
4. Drop completed-step chatter and replace it with compact state + references.
5. Do not discard material that is cheap now but expensive or impossible to reconstruct later.

Future utility should influence retention, but never override exactness or safety-critical evidence.
