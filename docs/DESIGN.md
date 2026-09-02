# Design

Adaptive Context Engineering treats context selection as a control problem rather than a fixed retrieval recipe.

## Core policy

1. **Activation gate** — no retrieval is a valid action.
2. **Route** — classify the context problem before choosing a retrieval strategy.
3. **Resolution ladder** — index/metadata → summary → extract → raw evidence.
4. **Specialist route** — load only the route needed for the task.
5. **Sufficiency gate** — expand on unresolved uncertainty, not just token pressure.
6. **Verification** — re-open fidelity-critical evidence before finalizing.

## Quality constraint

Optimization is valid only when quality does not regress against a comparable baseline. Token reduction alone is not success.

## Public Skill vs Runtime

The public skill expresses portable behavior using the Agent Skills format. Persistent event stores, bitemporal state, graph indexes, learned routing, and external memory adapters belong in a separate optional runtime layer.
