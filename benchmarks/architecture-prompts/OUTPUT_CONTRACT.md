# Architecture Generation Common Output Contract

All benchmark conditions must produce the same final JSON shape. The benchmark
compares architecture quality, not verbosity or condition-specific output
privileges.

The generator sees only the project introduction, functional requirements,
architecturally significant requirements/constraints supplied in the task, and
the condition prompt. Hidden reference architecture and evaluator alignment are
never generator inputs.

## Required JSON shape

```json
{
  "architecture": {
    "nodes": [
      {
        "id": "stable-local-id",
        "kind": "COMPONENT|DATA_STORE|EXTERNAL_SYSTEM|ACTOR",
        "name": "human-readable name",
        "responsibility": "one concise responsibility"
      }
    ],
    "edges": [
      {
        "from": "node-id",
        "to": "node-id",
        "relation": "CALLS|READS|WRITES|PUBLISHES|SUBSCRIBES|AUTHENTICATES|AUTHORIZES|ROUTES|REPLICATES|OTHER",
        "contract": "API/event/schema/protocol or other explicit interaction"
      }
    ],
    "state": [
      {
        "name": "mutable state or dataset",
        "owner": "node-id or explicit multi-writer protocol",
        "consistency": "required consistency/ordering semantics",
        "recovery": "recovery or rebuild mechanism"
      }
    ],
    "boundaries": [
      {
        "between": ["node-id-a", "node-id-b"],
        "kind": "MODULE|PROCESS|SERVICE|SYSTEM|TRUST|DATA",
        "drivers": ["requirement/asr/constraint ids or concise driver labels"],
        "enforcement_or_mitigation": "contract/isolation mechanism or null"
      }
    ]
  },
  "requirement_traceability": [
    {
      "requirement_id": "input requirement/asr/constraint id",
      "mechanism_node_ids": ["node-or-edge-adjacent node ids"],
      "mechanism": "how the architecture satisfies or handles it",
      "fitness_check": "measurable verification"
    }
  ],
  "decisions": [
    {
      "id": "decision-id",
      "choice": "chosen mechanism",
      "drivers": ["requirement/asr/constraint ids"],
      "alternatives": ["material alternative"],
      "accepted_tradeoffs": ["downside"],
      "reversal_condition": "condition that should reopen this decision"
    }
  ],
  "risks": [
    {
      "id": "risk-id",
      "description": "material unresolved risk",
      "affected_ids": ["node/decision ids"],
      "mitigation_or_next_evidence": "bounded next action"
    }
  ]
}
```

## Normalization rules

- Use stable local IDs; names may vary but IDs must be unique inside one output.
- Do not invent hidden requirement IDs. If the source requirement has no ID, the
  task adapter must assign one before generation.
- Every edge endpoint must reference an emitted node.
- Do not add a component solely to make the diagram symmetrical or fashionable.
- `requirement_traceability` must reference only input requirement IDs.
- Unknown architecture-changing facts belong in `risks`; do not silently resolve
  them by assumption.
- A missing optional mechanism is represented by an empty list or explicit null,
  not fabricated prose.

## Evaluation boundary

The common contract does not require a candidate to imitate the hidden reference
node names or topology. External adapters perform explicit node alignment for
reference-graph metrics. The same candidate is also evaluated independently for
traceability, state/boundary/failure invariants, scenario survival, complexity,
and blind human review.
