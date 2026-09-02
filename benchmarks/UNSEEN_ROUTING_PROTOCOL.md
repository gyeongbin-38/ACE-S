# Unseen Routing + Recovery Protocol v0.1

## Purpose

Evaluate the **frozen** ACE-S progressive-policy controller on task wording that was not authored for ACE-S.

This protocol is intentionally separate from the earlier authored RouterBench. The goal is not to optimize exact labels. It is to learn whether:

1. the Tiny Kernel can stay `DIRECT` on tasks that do not need extra context;
2. an `ACTIVE` task can select one useful coarse policy without loading the architecture;
3. one optional backup is enough for ambiguous boundaries;
4. a wrong manifest can be rejected instead of becoming a fatal route;
5. external tasks expose missing context families that the current taxonomy cannot represent.

## Controller freeze

The policy under test is pinned to:

`6e84f524aeb9bd761aa789445c1edb99cdadd9dd`

See [`FROZEN_CONTROLLER_V04.json`](FROZEN_CONTROLLER_V04.json).

The evaluation branch is `eval/unseen-routing-v04`. Policy files listed in the freeze manifest must not be changed on that branch while v0.1 is being evaluated.

## External prompt sources

The fixture references task IDs rather than rewriting prompts for ACE-S.

### Source A — Agent-Skills-for-Context-Engineering

- repository: `muratcankoylan/Agent-Skills-for-Context-Engineering`
- pinned commit: `272702e0bb1ff4f78d45fb7253da872da170d458`
- file: `researcher/benchmarks/router/prompts.jsonl`
- use here: conceptual/direct controls, implementation requests, context-history tasks, current telemetry/recommendation tasks.

### Source B — SkillRouter Eval Core

- repository: `zhengyanzhao1997/SkillRouter`
- pinned commit: `21f4bc31327a4d2beebfb454c159860ea21d8631`
- file: `data/eval_core/tasks.jsonl`
- use here: concrete file/tool/code/document/research execution tasks.

## Gold-label policy

ACE-S labels were created **after** the controller freeze.

For ambiguous prompts, the fixture stores an `acceptable_primary` set instead of forcing a single answer.

A more important distinction is `architecture_gap`:

- `WORKING_HISTORY` — the required context is a conversation/trajectory/session history rather than a repository, long document, external research set, or conflicting state.
- `DATA_ARTIFACT` — the required context is primarily a structured/binary/data artifact such as STL, PCAP, network topology JSON, or a game map rather than repository structure.

A gap label is **not** a proposed new production route. It records that the frozen four-domain taxonomy does not cleanly describe the task.

## Phase 1 — Activation

Output:

```json
{
  "activation": "DIRECT | ACTIVE",
  "primary": "CODE | DOCUMENT | RESEARCH | STATE | null",
  "backup": "CODE | DOCUMENT | RESEARCH | STATE | null"
}
```

Constraints:

- `DIRECT` must not load a primary/backup policy.
- `ACTIVE` chooses one primary candidate.
- `backup` is optional and singular.
- do not enumerate all candidates.

## Phase 2 — Manifest fit / bounded recovery

For an ACTIVE task, inspect only the selected manifest.

Output additionally:

```json
{
  "manifest_fit": true | false,
  "gap_detected": "WORKING_HISTORY | DATA_ARTIFACT | null"
}
```

If the manifest does not fit:

- reject it;
- use the single backup if it fits;
- otherwise record a taxonomy gap rather than fanning out through every manifest.

This benchmark does not reward inventing a new production policy on the holdout branch.

## Metrics

### Structural metrics

These do not depend on model prediction quality:

- `taxonomy_coverage_rate_active` — fraction of ACTIVE external tasks that can be described by at least one frozen primary domain.
- `taxonomy_gap_active_n` and gap family counts.

Structural coverage is reported even if a model later detects all gaps successfully.

### Prediction metrics

- activation accuracy;
- DIRECT no-policy-load rate;
- top-1 accuracy on taxonomy-covered ACTIVE tasks;
- top-2 candidate coverage on covered tasks;
- gap-detection rate after manifest mismatch;
- candidate-budget compliance;
- final route-or-gap resolution rate.

## Evidence levels

### Level 0 — architecture structure

Frozen taxonomy coverage only. No model required.

### Level 1 — single-model sanity pass

Useful for finding obvious failures, but not a stable performance claim when the same evaluator authors gold labels and predictions.

### Level 2 — independent repeated routing run

Requires a separate model/provider execution path, raw outputs, repetitions, and no policy edits against the holdout.

### Level 3 — end-to-end agent A/B

Required before claiming quality or token improvement in production use.

## Anti-overfit rules

1. Freeze controller before selecting/scoring external prompts.
2. Do not edit frozen policy files to improve v0.1.
3. Publish taxonomy gaps even if they lower apparent coverage.
4. Keep external source commits pinned.
5. Do not convert a gap into a new domain until it repeats on a broader external sample and real-agent traces.
6. A high model score cannot override poor structural taxonomy coverage.
