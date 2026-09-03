# ACE-S Runtime Trace Schema v0.1

Status: experimental measurement contract for real-runtime A/B traces.

This schema exists to prevent synthetic controller metrics from being silently promoted into real-runtime claims. A runtime trace MUST distinguish worker-visible context, controller-only context, certificate representation, tool/RPC activity, cache-aware expensive evaluations, algorithmic samples, latency, provenance, and final task quality.

## Principles

1. **Measure before estimate.** Use `status: measured` when the runtime exposes a value. Use `estimated` only when the estimator is named outside the metric value. Use `unavailable` with `value: null` when the runtime cannot observe it.
2. **Never infer missing historical metrics.** Old traces may be imported with unavailable fields; they must not be backfilled from unrelated counters.
3. **Certificate != summary.** A certificate is legal only for structured, explicitly certificate-capable evidence and must preserve the exact typed observed value (or an immutable hash/ref to it) plus provenance.
4. **Semantic evidence is never certificate-compressed.** Free text, source prose, and other semantic evidence remain full evidence when the worker needs them.
5. **Sample draws != expensive evaluations.** Record both. Memoization/cache hits can make them differ substantially.
6. **Final quality is first-class.** Efficiency claims do not count if the paired OFF/ON task quality regresses beyond the declared gate.

## JSONL envelope

One JSON object per line, ordered by increasing `seq`.

```json
{
  "schema_version": "0.1",
  "task_id": "repo-task-001",
  "event_id": "e0001",
  "seq": 1,
  "event_type": "task_start",
  "metrics": {}
}
```

Required common fields:
- `schema_version`: exactly `0.1`
- `task_id`: stable task identifier shared by the trace
- `event_id`: unique within the trace
- `seq`: strictly increasing positive integer
- `event_type`
- `metrics`: object; may be empty

## Metric value shape

Every numeric runtime metric uses:

```json
{"status":"measured","value":123.0}
```

or:

```json
{"status":"estimated","value":123.0}
```

or:

```json
{"status":"unavailable","value":null}
```

Allowed metric keys:
- `worker_visible_bytes`
- `worker_visible_tokens`
- `controller_only_bytes`
- `controller_only_tokens`
- `certificate_bytes`
- `certificate_tokens`
- `sample_draws`
- `wall_clock_ms`
- `tool_latency_ms`
- `model_latency_ms`

Values must be non-negative when present.

## Event types

### `task_start`
Must be the first event. Recommended fields: `condition` (`OFF` or `ON`), `surface`, `model`, `task_stratum`.

### `context_action_selected`
Fields: `action_id`, `action_type`, optional `fidelity`, optional `certificate_basis`.

### `tool_call_start`
Fields: `call_id`, `tool_name`, optional `action_id`.

### `tool_call_end`
Fields: `call_id`, `ok`; may carry `tool_latency_ms`. Every end must match an earlier start.

### `evidence_observed`
Fields:
- `evidence_id`
- `evidence_kind`: `structured` or `semantic`
- `certificate_capable`: boolean
- `provenance_refs`: non-empty array of stable source/raw references
- optional `value_sha256` for exact structured values

### `certificate_emitted`
Fields:
- `certificate_id`
- `evidence_id`
- `evidence_kind`: must be `structured`
- `schema_ref`: non-empty
- `exact_value_sha256`: non-empty immutable digest/ref for the exact observed typed value
- `provenance_refs`: non-empty

The referenced evidence must have been observed earlier, must be structured, must be certificate-capable, and its provenance must be preserved.

### `worker_context_exposed`
Fields:
- `representation`: `full` or `certificate`
- exactly one of `evidence_id` or `certificate_id`

Use metrics to record worker-visible bytes/tokens and certificate bytes/tokens.

### `controller_context_recorded`
Use metrics for controller-only bytes/tokens.

### `cache_hit` / `cache_miss`
Fields: `cache_key`. Optional `expensive_eval_id`.

### `expensive_eval`
Fields: `expensive_eval_id`, optional `eval_kind`. Unique expensive evaluation accounting is by unique ID, not by sample count.

### `sample_draw`
Use `sample_draws` metric. This is algorithmic sampling only.

### `model_call`
Fields: optional `model_call_id`; may carry `model_latency_ms`.

### `task_end`
Must be the last event. Fields:
- `passed`: boolean
- `quality_score`: number or null
- optional `failure_category`
- may carry final `wall_clock_ms`

## Required invariants

A conforming validator must reject at least:
- duplicate or non-monotonic event IDs/sequences;
- events after `task_end`;
- missing `task_start` or `task_end`;
- a `tool_call_end` without a preceding matching start;
- a certificate for semantic evidence;
- a certificate for evidence not marked certificate-capable;
- certificate provenance missing or detached from the observed evidence;
- a certificate without a schema and exact-value digest/ref;
- negative metric values;
- `status: unavailable` paired with a numeric value;
- `status: measured|estimated` paired with null;
- multiple task IDs in a single trace.

## Paired A/B reporting

For a same-task OFF/ON pair, report raw metrics before any aggregate score:
- final pass / quality score;
- worker-visible bytes/tokens;
- controller-only bytes/tokens;
- certificate bytes/tokens;
- tool/RPC calls;
- cache hits/misses;
- unique expensive evaluations;
- sample draws;
- wall-clock, tool, and model latency;
- provenance coverage;
- count of unavailable measurements.

Do not call a trace an end-to-end performance benchmark until a real model/runtime produced it and final task quality was scored.
