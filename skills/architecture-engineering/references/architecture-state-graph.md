# Architecture State Graph

The canonical architecture artifact is a typed decision/evidence graph. Diagrams and prose are views over this graph, not the source of truth.

## 1. Why a graph

Architecture is primarily relationships and decisions. A box diagram can look complete while omitting:
- why a boundary exists;
- who owns mutable state;
- which ASR a mechanism satisfies;
- where trust is enforced;
- how failure propagates;
- which evidence supports a claim;
- what condition should reopen a decision.

A typed graph makes these relations inspectable and incrementally updateable.

## 2. Core node types

### Intent nodes
- `REQUIREMENT`
- `ASR`
- `HARD_CONSTRAINT`
- `NON_GOAL`
- `UNKNOWN`

### Architecture nodes
- `COMPONENT`
- `BOUNDARY`
- `STATE`
- `FLOW`
- `INTERFACE`
- `DEPLOYMENT_UNIT`
- `TRUST_ENFORCEMENT`

### Decision/evaluation nodes
- `DECISION`
- `OPTION`
- `SCENARIO`
- `RISK`
- `PROOF_OBLIGATION`
- `FITNESS_CHECK`

### Evidence nodes
- `INTENT_EVIDENCE`
- `OBSERVED_EVIDENCE`
- `MEASUREMENT`

## 3. Minimum typed edges

Use explicit edge semantics rather than free-form links.

Examples:
- `ASR --SATISFIED_BY--> FLOW|BOUNDARY|STATE|DECISION`
- `HARD_CONSTRAINT --RESTRICTS--> DECISION|BOUNDARY|DEPLOYMENT_UNIT`
- `DECISION --SELECTS--> OPTION`
- `DECISION --REJECTS--> OPTION`
- `DECISION --AFFECTS--> COMPONENT|BOUNDARY|STATE|FLOW`
- `BOUNDARY --SEPARATES--> COMPONENT`
- `STATE --OWNED_BY--> COMPONENT`
- `FLOW --TRAVERSES--> INTERFACE|BOUNDARY`
- `FLOW --READS|WRITES--> STATE`
- `TRUST_ENFORCEMENT --ENFORCES--> BOUNDARY`
- `SCENARIO --ATTACKS--> ASR|DECISION|FLOW|BOUNDARY`
- `RISK --EXPOSED_BY--> SCENARIO`
- `FITNESS_CHECK --VERIFIES--> ASR|DECISION|BOUNDARY|FLOW|STATE`
- `PROOF_OBLIGATION --PROVES--> DECISION|BOUNDARY|FLOW|STATE|ASR`
- `EVIDENCE --SUPPORTS|CONTRADICTS--> any architecture/decision claim`

## 4. Canonical state shape

A practical serialized state may use collections rather than a generic graph database:

```text
architecture_state
  metadata
  intent
    requirements[]
    asrs[]
    hard_constraints[]
    non_goals[]
    unknowns[]
  components[]
  boundaries[]
  state[]
  interfaces[]
  critical_flows[]
  decisions[]
  scenarios[]
  risks[]
  proof_obligations[]
  fitness_checks[]
  evidence[]
  traceability_edges[]
```

Every significant object should have a stable `id` so diagrams, ADRs, tests, and implementation evidence can refer to the same decision graph.

## 5. Traceability requirements

For every critical ASR require at least one path:

`ASR → architecture mechanism → fitness check`

For every high-lock-in decision require:

`driver/ASR/constraint → decision → selected option → affected architecture nodes → kill condition`

For every critical mutable state require:

`state → owner or explicit multi-writer protocol → recovery path`

For every material trust boundary require:

`constraint/ASR → boundary → enforcement point → security fitness check or inspection procedure`

## 6. Evidence status

Claims should expose one of:
- `OBSERVED` — directly supported by current evidence;
- `ACCEPTED_INTENT` — accepted requirement/decision but not yet implemented;
- `INFERRED` — reasoned from evidence with explicit confidence;
- `UNRESOLVED` — material information missing.

Do not silently promote `INFERRED` to `OBSERVED`.

## 7. Views

Generate views from the same state according to audience/question:
- context/system view
- module/component view
- deployment view
- data/state ownership view
- trust boundary view
- critical flow sequence view
- decision/ADR view
- fitness/conformance view

Do not force one mega-diagram to carry every concern.

## 8. Incremental update

When evidence or requirements change:
1. update the affected node;
2. follow incoming/outgoing traceability edges;
3. reopen only decisions whose drivers, kill conditions, or proof obligations changed;
4. rerun relevant scenarios/fitness checks;
5. regenerate affected views.

This is the architecture equivalent of incremental compilation: recompute the decision neighborhood, not the entire design.
