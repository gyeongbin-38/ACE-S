# Repository Behavior Policy Freeze v0.5.4

Status: **FROZEN — development policy only**

This freeze closes policy selection on the 14 previously observed development tasks. It does not claim unseen generalization.

## Frozen policy

- architecture: pure multi-scale Behavior Windows
- spans: `[4, 16, 24]`
- max windows per frontier file: `5`
- merge gap: `0`
- exact quota: `5`
- frontier top-k: `8`
- semantic judge during selection: **none**
- hybrid evidence during selection: **none**

## Hard gate

- frontier recall: `14/14`
- Behavior Witness fidelity: `14/14`
- false-confident direct selection: `0`

Context cost on the development suite:

- worst-case unique source lines: `960`
- mean unique source lines: `656.6428571428571`
- actual maximum emitted windows per task: `40`
- mean emitted windows per task: `28.928571428571427`

## Selection lineage

1. Audited fixed-span grid: 108 policies, 0 passed 14/14.
2. Multi-scale v0.5.3: 105 policies, 12 passed; winner `[4,8,16,24]/5/0`.
3. Exhaustive non-empty subset boundary v0.5.4: 90 policies over subsets of `{4,8,16,24}`, max-windows `{4,5}`, gaps `{0,1,2}`.
4. Final bounded winner: `[4,16,24]/5/0`.

No policy with `max_windows=4` passed. The best `4`-window boundary reached `13/14` and failed `chi-route-param-context-001`, witness `context.go:10-20`, with `0` visible witness lines versus `6` required.

## Clean rerun

The v0.5.4 subset search was executed twice from the same source commit:

`761b4a4c5150c79f912bc7387c451aa66bf9e987`

Both attempts produced the same inner result JSON byte-for-byte:

`sha256:80bf28cf3dae4e035ad3d7fa53a89ce513dae40376da0b50df31a39ecec05abe`

Workflow run: `33749954293`.

The machine-readable freeze manifest is:

`benchmarks/runtime-traces/pilots/repo-behavior-policy-freeze-v0.5.4.json`

## Freeze rule

Do not tune spans, window budget, merge gap, retrieval coefficients, selector coefficients, or witness rules after opening fresh Suite A. Any such change starts a new development lineage and requires a new sealed suite.

## Next evaluation

1. Fresh sealed Suite A: deterministic frontier + Behavior Witness evaluation.
2. Separate Suite B: Luna xhigh blind semantic evaluation using evidence cards only. Luna receives no expected file, expected symbol, witness location, or source-label metadata.
