# ACE-S Portable Skill Mode

Goal: preserve the Bounded Context Scheduler philosophy when ACE-S is used as a portable skill in environments where a full controller runtime is unavailable, including web ChatGPT-style workflows and Codex-style coding agents.

## Two operating modes

### Native controller mode
Preferred when a harness/runtime is available.

- external epistemic state
- measurable cost model
- bounded rollout scheduler
- source×fidelity actions
- recoverable raw evidence
- worker sees only compact evidence/state/capsule

### Portable skill mode
Fallback for web/model-only environments.

Do not emulate the entire controller in prose. Keep a tiny kernel and perform only the minimum scheduling decisions needed for the current task.

Core portable loop:

```text
1. Is current context already sufficient? If yes, answer/STOP.
2. Name the single material unknown most likely to change the answer.
3. Generate at most 2–4 candidate context actions for that unknown.
4. Prefer the action with the best expected decision value per effective cost.
5. Read only that context at the minimum sufficient fidelity; skip ladder levels when justified.
6. Update a compact state: known / unknown / conflict / exactness / freshness.
7. Drop, abstract, or retain context based on likely reuse and reacquisition cost.
8. Repeat only while another action is likely to materially improve the answer.
```

## Portable state capsule

Keep this small and update it rather than restating history.

```yaml
goal: ...
known:
  - ...
unknown:
  - ...
conflicts:
  - ...
constraints:
  exact: []
  fresh: []
selected_evidence:
  - ref: ...
    supports: ...
next_material_unknown: ...
```

## Candidate-action discipline

Candidate actions should be concrete and bounded, for example:
- inspect repository tree/index
- search one symbol
- open one exact code range
- inspect one document section
- search current public sources
- verify one conflicting claim
- stop

Do not load every architecture document, skill reference, README, or tool description for awareness.

## Codex-oriented guidance

For repository work:
- start from task-local symbols/files/tests instead of reading the repository broadly;
- read root/project instructions only when they govern the touched scope;
- use search/index before broad raw reads;
- jump directly to exact implementation/tests when exact behavior is required;
- keep compact working state and references to raw files rather than copying large code regions forward;
- re-open raw evidence when exact implementation details are needed.

## Web GPT-oriented guidance

For web/file/research work:
- infer the smallest source class needed first;
- retrieve one high-value source/section at a time;
- distinguish freshness requirements from generic mentions of "current";
- preserve citations/refs so raw evidence is recoverable;
- avoid accumulating all search results in working context;
- stop when remaining uncertainty is unlikely to change the answer.

## Safety boundary

Portable mode is an approximation of the native scheduler. It has no reliable access to exact transition probabilities or full runtime cost accounting. Therefore use bounded qualitative estimates and prefer reversible actions when uncertain.

Do not claim synthetic scheduler benchmark numbers as portable web/Codex end-to-end gains until separately evaluated.
