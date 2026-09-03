# Architecture Synthesis Research Notes

Status: experimental research notes. These references motivate design choices; they do not establish that the current ACE-S architecture-engineering method is state of the art.

## Current hypothesis

A strong LLM architecture workflow should not optimize for the most detailed diagram or the largest catalog of patterns. It should improve the correctness of **relationships and decisions** under explicit requirements while minimizing unjustified irreversible commitments.

The experimental method therefore separates:

1. semantic perception of requirements/ASRs/unknowns;
2. architecture decision-frontier generation;
3. deterministic constraint and structural validation;
4. scenario-based risk/tradeoff attack;
5. Pareto filtering rather than hidden utility weights;
6. proof obligations and executable/inspectable fitness checks;
7. incremental architecture state with decision/evidence traceability.

## Research influences

### Architecture Tradeoff Analysis Method (ATAM)

CMU Software Engineering Institute, Kazman et al.

ATAM motivates treating architecture as a quality-attribute tradeoff problem rather than a pattern-selection exercise. Particularly relevant ideas are quality-attribute scenarios, risks, sensitivity/tradeoff points, and iterative candidate analysis/refinement.

ACE-S adaptation:
- use measurable ASR/scenario attacks before candidate promotion;
- preserve risks/sensitivity/kill conditions;
- do not collapse competing qualities into one score without explicit utility weights.

References:
- Rick Kazman et al., *The Architecture Tradeoff Analysis Method*, CMU/SEI-98-TR-008, 1998.
- Rick Kazman, Mark Klein, Paul Clements, *ATAM: Method for Architecture Evaluation*, CMU/SEI-2000-TR-004, 2000.

### Quality Attribute Workshop (QAW) / early scenario analysis

SEI work on QAW complements ATAM by eliciting/analyzing quality scenarios before a complete architecture exists.

ACE-S adaptation:
- convert vague non-functional requirements into architecture-significant scenarios early;
- distinguish ASRs from requirements that do not materially change architecture.

### R2ABench

Minxiao Li et al., *Benchmarking Requirement-to-Architecture Generation with Hybrid Evaluation*, arXiv:2604.06683, 2026.

R2ABench provides real requirement-to-architecture projects and a layered evaluation design. Its reported results are especially important for this project: modern LLMs can produce valid diagrams and identify architecture entities yet remain weak at relation-level reasoning, with hallucinated/missing edges and structural fragmentation.

ACE-S adaptation:
- make relational correctness primary over box completeness;
- require explicit critical-flow hops, state ownership, trust enforcement, and ASR traceability;
- keep structural graph metrics and human blind review in the planned evaluation;
- do not assume an agentic workflow is better merely because it has more agents/passes.

Public human-review tooling associated with R2ABench also demonstrates useful blind-review dimensions including completeness, faithfulness, architectural rationality, traceability, and readability.

### ARLO

Tooraj Helmi, *ARLO: A Tailorable Approach for Transforming Natural Language Software Requirements into Architecture using LLMs*, arXiv:2504.06143, 2025.

ARLO separates LLM-based identification of architecturally relevant requirements from a matrix of architecture choices and uses integer linear programming for architecture selection. It also emphasizes traceability from requirements to selected choices.

ACE-S adaptation/difference:
- preserve the semantic-vs-deterministic split;
- use deterministic feasibility/compatibility checks where possible;
- preserve requirement→decision traceability;
- do **not** produce a universal single optimum from implicit weights. Without explicit stakeholder utility weights, keep the feasible Pareto frontier and identify the next measurement that can change it.

### LLM-supported architecture evaluation

Rafael Capilla et al., *Towards Supporting Quality Architecture Evaluation with LLM Tools*, arXiv:2603.28914, 2026.

The work provides evidence that LLM assistance can help identify risks, sensitivity points, and tradeoffs in quality-attribute scenarios.

ACE-S adaptation:
- use LLM reasoning as a targeted scenario/risk analyst;
- keep hard constraints and structural invariants in deterministic gates;
- target additional red-team reasoning at architecture hotspots rather than running an always-on multi-agent debate.

### Software Architecture Meets LLMs — systematic review

Larissa Schmid et al., *Software Architecture Meets LLMs: A Systematic Literature Review*, arXiv:2505.16697, 2025.

The review reports increasing use of LLMs in software architecture while noting that many approaches still rely on relatively simple prompting and that areas such as architecture conformance remain underexplored.

ACE-S adaptation:
- treat generation, review, and conformance as distinct work modes;
- make the target architecture machine-checkable through contracts/fitness functions rather than leaving conformance as prose.

### Architecture Decision Records / decision governance

Architecture Decision Records motivate preserving context, alternatives, consequences, and rationale near important decisions.

ACE-S adaptation:
- high-lock-in decisions require drivers, alternatives, kill/reversal conditions, and evidence;
- missing rationale is `UNRESOLVED`, not filled with invented certainty;
- architecture diagrams are views; the decision/evidence graph is the durable reasoning artifact.

### Balanced relationship/coupling ideas

Vlad Khononov's Balanced Coupling work and the public `alexei-led/architect` project highlight an important distinction: coupling is not inherently bad; architecture quality depends on whether relationship strength is appropriate for the distance and expected change.

ACE-S uses an independently phrased **Boundary Balance** abstraction:
- separation pressure;
- cohesion pressure;
- change likelihood;
- chosen boundary distance;
- explicit mitigation when high distance is required despite cohesion pressure.

No numeric Balanced Coupling formula is copied into the ACE-S method. The purpose is to prevent both needless decoupling and distributed-monolith boundaries.

## Distinctive experimental claims to test

The following are hypotheses, not established results:

1. **Minimum-architecture-first** reduces unjustified distributed boundaries compared with noun-driven decomposition.
2. **Separation-vs-cohesion boundary balance** reduces distributed-monolith seams without blocking required isolation.
3. **Typed architecture state graphs** improve requirement/ASR traceability and make relation gaps easier to detect than diagram-first output.
4. **Proof obligations** reduce fabricated rationale and missing state/trust/failure semantics.
5. **Hard-gate + Pareto selection** is safer than a single weighted architecture score when stakeholder utility weights are unknown.
6. **Targeted hotspot red-team** yields more stable quality/context tradeoffs than always-on multi-agent debate.
7. **Progressive architecture-policy/evidence loading** can reduce context exposure without architecture-quality regression.
8. **Incremental decision-neighborhood re-entry** can update an architecture more safely than full redesign when one requirement/evidence item changes.

## Claim boundary

Do not call this method "best", "SOTA", or superior to other architecture-generation approaches until the preregistered protocol in `benchmarks/ARCHITECTURE_SYNTHESIS_PROTOCOL.md` has been executed on sealed external projects with relation-level structural metrics, deterministic hard-failure checks, and blinded human review.
