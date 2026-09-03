# Luna Blind Semantic Evaluation Protocol v1

Purpose: evaluate whether frozen ACE-S evidence cards are sufficient for a strong semantic judge to identify the implementation location or abstain, without leaking benchmark labels.

## Separation from policy selection

The development policy is already frozen at:

- spans: `[4,16,24]`
- max_windows: `5`
- merge_gap: `0`

Luna MUST NOT be used to change these values or any development retrieval/ranking coefficient.

## Inputs Luna may receive

For each Suite B task Luna receives only:

1. the natural-language task/request;
2. the frozen ACE-S evidence cards emitted for the frontier;
3. file paths that are naturally part of those evidence cards;
4. an opaque task id.

## Inputs Luna must not receive

Luna MUST NOT receive:

- expected file;
- expected symbol/function/class;
- Behavior Witness line ranges;
- required-region metadata;
- source blob labels identifying the answer;
- prior benchmark outcome;
- development-task analogues or hints;
- scorer feedback before its answer is final.

## Required Luna output

Return exactly one JSON object:

```json
{
  "task_id": "opaque-id",
  "decision": "select|abstain",
  "selected_file": "path/or/null",
  "confidence": 0.0,
  "evidence_refs": ["card-id:window-id"],
  "reason": "brief evidence-grounded explanation"
}
```

Rules:

- `selected_file` must be one of the presented evidence-card paths when `decision=select`.
- Use `abstain` if the cards do not justify a unique answer.
- Do not infer from repository popularity, memorized code layout, benchmark naming, or external browsing.
- Do not request hidden labels.

## Execution controls

Capture for every run:

- Luna model/version identifier;
- reasoning level (`xhigh` when available);
- prompt/protocol blob SHA;
- exact evidence packet SHA;
- timestamp;
- temperature / seed / deterministic settings when exposed;
- raw Luna response before scoring.

## Scoring

Scoring occurs only after Luna's response is persisted.

Primary metrics:

- correct selection rate;
- false-confident selection rate;
- abstention rate;
- conditional accuracy when selecting.

Secondary metrics:

- evidence-card line cost;
- frontier size;
- judge invocation rate;
- confidence calibration.

No failed Suite B example may be used to modify the frozen policy and then be counted again as unseen evidence.
