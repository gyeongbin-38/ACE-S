# Architecture Synthesis Evaluation Protocol

Status: **protocol only — no model-quality claim yet**.

The purpose of this benchmark is to test whether the architecture-engineering method improves requirement-to-architecture quality without hiding failures behind a single LLM-judge score.

## 1. Primary research question

Does evidence-constrained, proof-carrying synthesis improve **relational correctness, requirement traceability, and architecture risk handling** over a normal single-pass architecture prompt while keeping generated complexity bounded?

## 2. Conditions

Use the same model, temperature/sampling policy, tool access, and task inputs for all conditions.

### A — Direct
A normal high-quality prompt: design an architecture from the supplied requirements.

### B — ASR/Scenario
Extract architecturally significant requirements and quality scenarios before generating one architecture.

### C — Evidence-Constrained Synthesis
Use:
- minimum architecture baseline;
- decision frontiers;
- separation vs cohesion boundary pressure;
- explicit state/trust/failure relations;
- hard-constraint elimination;
- Pareto comparison when alternatives remain.

### D — Proof-Carrying Synthesis
Condition C plus:
- typed architecture state graph;
- proof obligations;
- requirement/ASR traceability edges;
- counterexample/kill conditions;
- fitness functions;
- deterministic architecture-contract validation before promotion.

This is the target method. Do not alter it after sealed test outputs are observed; changes require a new benchmark version or untouched fold.

## 3. Dataset strata

### External reference-architecture stratum
Prefer a public requirement-to-architecture benchmark such as R2ABench where requirements and expert/reference architecture views are available.

Use project-level splits. A project must not appear in both development and sealed evaluation through alternate prompts or views.

### Existing-system redesign stratum
Use public repositories with:
- requirement/issue/ADR or documented architecture intent;
- observable code/deployment/state relations;
- a historical architecture change or independently reviewable target.

Freeze repository SHAs before execution.

### Counterfactual requirement stratum
Create paired requirement changes where the expected architectural consequence is directional rather than a single reference diagram, for example:
- add/remove strict tenant isolation;
- add/remove immediate consistency;
- raise/lower scale independently for one workload;
- add offline operation;
- change zero-downtime deployment requirement;
- remove a previously mandatory external provider.

The purpose is to test whether decisions respond causally to architecture-changing requirements rather than merely generating plausible static diagrams.

## 4. Measurement layers

### L0 — Syntax / parse validity
- output schema validity
- diagram parse validity when a diagram is requested

### L1 — Structural reference metrics
When reference architecture graphs exist:
- node precision / recall / F1
- relation/edge precision / recall / F1
- edge hallucination rate
- connectedness / fragmentation

Relation metrics are primary. High node F1 cannot compensate for low edge fidelity.

### L2 — Requirement coverage and traceability
- critical ASR coverage
- critical ASR → mechanism traceability
- requirement → decision traceability
- mechanism → fitness-check traceability
- unsupported architecture claims

### L3 — Architecture contract invariants
Use deterministic checks where applicable:
- hard-constraint violations
- critical relation gaps
- mutable-state ownership ambiguity
- trust boundary without enforcement
- critical flow without failure behavior
- high-distance boundary without separation pressure
- high-distance boundary with unresolved cohesion pressure
- high-lock-in decision without alternatives/reversal condition

### L4 — Scenario survival
For prioritized quality scenarios, evaluate whether the design contains a credible causal mechanism and whether the scenario exposes:
- risk
- sensitivity point
- tradeoff point
- missing mitigation

Scenario evaluators must see the same requirements and candidate architecture, not the hidden reference architecture unless the scoring method explicitly requires it.

### L5 — Human blind review
Blind candidate/model/workflow identity.

Suggested dimensions:
- completeness
- faithfulness / unsupported claims
- architectural rationality
- traceability
- readability
- state/consistency correctness
- failure/recovery adequacy
- boundary justification

Use architecture practitioners where possible. Measure inter-rater agreement; do not report a single reviewer as ground truth.

### L6 — Complexity / regret proxies
Report rather than blindly minimize:
- component count
- distant boundary count
- state store count
- async channel count
- coordinated-release edges if observable
- high-lock-in decision count
- unresolved architecture-changing unknowns
- missing migration paths

## 5. No single headline score by default

Report a metric vector and Pareto comparison.

A scalar score is allowed only after metric directions and stakeholder/research utility weights are preregistered. Never choose weights after seeing condition results.

## 6. Quality-first gate

A context/token/runtime reduction counts as an improvement only if architecture quality is non-inferior on the preregistered primary quality metrics.

Efficiency must not compensate for:
- hard-constraint regression;
- edge hallucination regression;
- critical ASR coverage regression;
- state/trust/failure correctness regression.

## 7. Contamination controls

- Separate method-authoring/development tasks from sealed tasks.
- Freeze prompts, model settings, evaluation code, task membership, references, and primary gates before sealed execution.
- Hash/freeze method files and evaluators.
- Do not tune the method on sealed failures.
- A method change requires a new untouched evaluation fold.
- Record benchmark source/version and model date/version.

## 8. Ablations

At minimum compare D against:
1. D without boundary balance;
2. D without proof obligations;
3. D without scenario attack;
4. D without deterministic contract gate;
5. D with all architecture references preloaded instead of progressive loading.

This identifies whether improvement comes from the architecture method rather than simply longer instructions.

## 9. Context-efficiency measurements

When runtime instrumentation is available measure:
- policy/reference bytes or tokens loaded;
- repository/document evidence bytes or tokens exposed to the architecture worker;
- retrieval/tool calls;
- architecture-changing evidence fetches;
- irrelevant evidence loads;
- reacquisition calls;
- wall-clock latency.

Compare progressive loading to full-method preload only after quality non-inferiority is established.

## 10. Promotion gate for a strong public claim

Do not claim "best" or "state of the art" unless all are true:
- sealed external projects were not used to author/tune the method;
- target method beats Direct on relation/edge fidelity with uncertainty reported;
- target method does not regress critical requirement coverage;
- deterministic hard-failure rate decreases;
- blind human review prefers or rates the target method higher with acceptable agreement;
- gains reproduce across more than one model family or are explicitly scoped to one model;
- evaluation artifacts and claim boundaries are published.

Until then, describe the method as **experimental evidence-constrained architecture synthesis**.

## 11. External benchmark alignment

R2ABench is especially relevant because its published evaluation separates syntax validity, structural graph metrics, multi-dimensional scoring, and architecture anti-pattern detection, and reports relation-level reasoning as a major LLM weakness. Its public human-review tooling also uses blind candidate labels and exposes requirements alongside reference/candidate architecture views.

Our benchmark extends that direction with state ownership, boundary balance, proof obligations, scenario survival, and decision/fitness traceability rather than replacing the original structural metrics.
