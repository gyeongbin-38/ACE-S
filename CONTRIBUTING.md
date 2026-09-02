# Contributing to ACE-S

Contributions are welcome. ACE-S follows one hard rule:

> **Quality first, efficiency second.** A context optimization is not a win if it lowers verified task quality, exactness, or recoverability.

## Where changes belong

| Change | Location |
|---|---|
| Activation/routing policy | `skills/adaptive-context-engineering/SKILL.md` |
| Specialist behavior | `skills/adaptive-context-engineering/references/` |
| Trigger/behavior examples | `skills/adaptive-context-engineering/evals/evals.json` |
| Benchmark protocol/results | `benchmarks/` |
| Public usage docs | `docs/` or `examples/` |
| Validation tooling | `scripts/` and `.github/workflows/` |

Keep `SKILL.md` compact. If a rule only applies to one problem class, prefer a specialist reference so the skill can use progressive disclosure on itself.

## Before opening a PR

Run:

```bash
python scripts/validate_skill.py
python scripts/validate_benchmarks.py
```

Then check:

1. behavior changes have an eval or reproducible example;
2. new specialist references are linked from `SKILL.md`;
3. exact/provenance-critical information is not replaced by lossy summaries;
4. default context did not grow without a clear quality reason;
5. synthetic, retrieval-policy, and end-to-end model-quality claims remain separate;
6. regressions and no-uplift cases are documented, not hidden.

## Benchmark contributions

For same-model ACE-S OFF vs ON results, follow [`benchmarks/AGENT_AB_PROTOCOL.md`](benchmarks/AGENT_AB_PROTOCOL.md).

Useful submissions include:

- raw task-level results;
- model/runtime versions;
- controlled tool/permission conditions;
- correctness rubric;
- input/output tokens;
- tool calls and retrieval rounds;
- latency;
- trigger precision;
- failure categories.

A benchmark that shows ACE-S regressing is valuable evidence and should be submitted.

## Designing new rules

A good new ACE-S rule should answer:

```text
Trigger: when does this rule apply?
Action: what should the agent do differently?
Stop: when is the context sufficient?
Risk: how could the rule lose fidelity or over-trigger?
Eval: how can we detect that regression?
```

Avoid rules that simply say "search more," "summarize everything," or "always use semantic retrieval." ACE-S exists to make context behavior conditional on the task.

## Pull requests

Keep PRs focused. Explain the context failure being addressed and the before/after behavior. The PR template includes quality, evaluation, and provenance checks.

## Security

Do not publish secrets, private data, or exploitable security details in examples or issues. See [`SECURITY.md`](SECURITY.md) for vulnerability reporting guidance.
