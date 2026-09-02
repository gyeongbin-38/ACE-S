## Summary

What context problem does this change improve?

## Change type

- [ ] Skill/controller behavior
- [ ] Specialist reference
- [ ] Eval
- [ ] Benchmark / result
- [ ] Integration / example
- [ ] Documentation / repository UX
- [ ] CI / tooling

## Quality-first evidence

Describe the baseline and why this change should preserve or improve task quality.

If this is an efficiency optimization, show why it does not trade away correctness, exactness, or recoverability.

## Evaluation

- [ ] Added/updated an eval for behavior changes
- [ ] Ran `python scripts/validate_skill.py`
- [ ] Ran `python scripts/validate_benchmarks.py` when benchmark files changed
- [ ] Documented regressions/no-uplift cases
- [ ] Kept synthetic/retrieval metrics separate from end-to-end answer-quality claims

## Context impact

What changes in default context loading?

```text
Before:
After:
```

## Provenance / exactness impact

Could this change summarize, compact, or discard information that must remain exact or recoverable? If yes, explain the safeguard.

## Checklist

- [ ] `SKILL.md` remains compact; specialist detail lives in `references/`
- [ ] New references are linked from `SKILL.md` when needed
- [ ] No unrelated context is loaded by default
- [ ] Public benchmark claims are reproducible from committed evidence
