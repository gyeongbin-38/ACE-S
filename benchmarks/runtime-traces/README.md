# ACE-S Real-Runtime A/B Harness

Status: experimental measurement harness. It does not make performance claims by itself.

## What exists

The runtime benchmark layer now has four separate responsibilities:

1. `runtime_trace_writer.py` — surface adapters emit normalized JSONL facts.
2. `validate_runtime_trace.py` — rejects invalid traces and illegal semantic certificates.
3. `compare_runtime_ab.py` / `compare_runtime_ab_suite.py` — Quality First paired gates.
4. `run_runtime_ab_harness.py` — executes frozen tasks through an external OFF/ON adapter while withholding ground truth.

The frozen first real-repository pilot is:

```text
benchmarks/runtime-traces/pilots/repo-localization-v0.1.json
```

It contains six repository-localization tasks across Requests, Django, Zod, Gin, Kubernetes, and Gson.

## Ground-truth boundary

The harness reads `expected_file`, but the adapter does not.

For each task the adapter receives only:

```json
{
  "task_id": "...",
  "task_stratum": "repository-local",
  "repository": "owner/repo",
  "commit_sha": "...",
  "prompt": "..."
}
```

The harness scores the returned answer after the adapter exits, then overwrites the trace's final `task_end.passed` and `quality_score` fields before validation and A/B comparison.

This prevents a runtime adapter or model prompt from accidentally receiving benchmark ground truth.

## Adapter CLI contract

An adapter command must accept:

```text
--task <public-task.json>
--condition OFF|ON
--trace-out <trace.jsonl>
--result-out <result.json>
```

`result.json` must contain:

```json
{"answer":"repository/relative/path.ext"}
```

The trace must follow `TRACE_SCHEMA_V0.1.md`, use the same `task_id`, and declare the requested OFF/ON condition in `task_start`.

The adapter is responsible for measuring only what its runtime can actually observe. Missing metrics must remain `unavailable`; do not infer token counts, latency, cache behavior, or bytes from unrelated counters.

## Example execution

```bash
python scripts/run_runtime_ab_harness.py \
  benchmarks/runtime-traces/pilots/repo-localization-v0.1.json \
  --adapter "python adapters/my_runtime_adapter.py" \
  --out-dir benchmarks/runtime-traces/runs/my-runtime-v0.1 \
  --require-pass
```

Do not commit real run outputs until model/version, tool permissions, repository access mode, and evaluator conditions are recorded.

## Current gate

A suite passes only when:

1. no OFF-passing task becomes an ON failure;
2. all paired quality-score comparisons satisfy the declared non-inferiority tolerance;
3. at least one paired measured efficiency metric improves materially.

Aggregate savings cannot hide a per-task quality regression.

Metrics are reported separately rather than collapsed into one score:

- worker-visible bytes/tokens,
- controller-only bytes/tokens,
- certificate bytes/tokens,
- tool/RPC calls,
- unique expensive evaluations,
- algorithmic sample draws,
- tool/model/wall-clock latency,
- provenance coverage,
- final pass/quality.

## Certificate rule

A worker-visible certificate is legal only for structured, explicitly certificate-capable evidence with exact typed-value identity and preserved provenance. Semantic/free-text evidence may not be certificate-compressed.

## Next adapters

The harness is intentionally surface-neutral. The next useful implementations are thin adapters for:

- Codex,
- JARVIS/Paseo,
- another independently runnable coding agent such as OpenCode.

Web ChatGPT can be evaluated only when the environment exposes enough runtime instrumentation to generate the same trace contract; unavailable internal metrics must remain unavailable rather than estimated after the fact.
