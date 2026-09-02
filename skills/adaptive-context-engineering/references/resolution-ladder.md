# Resolution Ladder

Use when context is large enough that reading everything would dilute attention or waste tokens.

## Procedure
1. Inspect index/metadata first.
2. Read compact summaries for candidate regions.
3. Pull exact extracts only for candidate regions that can change the answer.
4. Read full/raw material only for fidelity-critical details or unresolved uncertainty.

## Escalation signals
Escalate when a required claim lacks evidence, candidate summaries conflict, the query asks for exact text/numbers, or the lower-resolution view omits a dependency needed for the conclusion.

## Stop condition
Stop when additional context has low expected decision value. Do not expand merely because budget remains.
