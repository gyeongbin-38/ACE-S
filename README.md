# Adaptive Context Engineering Skill

A portable Agent Skill for deciding **what context to load, at what resolution, and when to stop**.

The goal is not "use fewer tokens" by itself. The goal is to preserve or improve task quality while reducing irrelevant context, stale state, redundant retrieval, and unnecessary tool/file loading.

## Why this exists

Long-context agents often fail in two opposite ways:

- too little context → missing dependencies, stale assumptions, unsupported claims;
- too much context → distraction, tool overload, higher latency/cost, and harder verification.

This skill uses a compact routing policy, a resolution ladder, specialist references, and a sufficiency gate.

## Install

With the open `skills` CLI:

```bash
npx skills add gyeongbin-38/ACE-S-adaptive-context-engineering-skill --skill adaptive-context-engineering
```

Or install directly from the skill directory URL.

The Agent Skills format is portable; support varies by client.


## Personal daily use

This skill is designed to stay out of the way on simple tasks and activate when context management can materially improve reliability or efficiency. It is especially useful for:

- deep research and multi-source synthesis;
- coding and repository investigation;
- long documents or large tool outputs;
- multi-step workflows and handoffs;
- conflicting, changing, or historical state;
- tasks where exact evidence and provenance matter.

For short one-shot questions, casual conversation, and creative writing, the activation gate should prefer direct answering with no extra retrieval.

## Design

The main `SKILL.md` stays deliberately small. It loads specialist guidance only when needed:

- `coding.md`
- `temporal.md`
- `research.md`
- `plan-aware.md`
- `evidence-and-provenance.md`
- `resolution-ladder.md`

This applies progressive disclosure **inside the skill itself**.

## Benchmark status

### Synthetic mechanism benchmark

A controlled synthetic benchmark was used to compare context-selection mechanisms before release. It is useful for architecture selection, not a claim about end-to-end LLM performance.

See `benchmarks/README.md` and `benchmarks/results/synthetic-v0.1.csv`.

### Required before claiming real-world uplift

Before publishing performance claims, run A/B evaluations through real agent harnesses:

- baseline: same agent/model without the skill;
- treatment: same agent/model with the shipped `SKILL.md`;
- repeated runs;
- trigger precision / near-miss tests;
- task correctness;
- input tokens;
- latency;
- negative cases where the skill does not help.

Recommended harnesses include `agent-skill-eval`, `agent-skills-eval`, or an equivalent reproducible setup.

## Principles

1. No retrieval is a valid action.
2. Resolution before volume.
3. Structure before global semantic search when structure exists.
4. Future utility matters in multi-step work.
5. Summaries are views, not source of truth.
6. Expand on insufficiency/uncertainty, not merely token pressure.
7. Correctness first; efficiency second.

## License

MIT
