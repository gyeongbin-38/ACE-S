# ACE-S µKernel

Goal: preserve task quality while exposing the worker to the least control context that can still recover exact evidence.

## Loop

1. **Sufficiency** — if supplied context already supports the material answer, `DIRECT`.
2. **Signal** — otherwise emit only the compact `SignalVector`; do not scan policies for awareness.
3. **Decide** — resolve one next `ContextDirective` from the compiled policy. Specialization is optional.
4. **Acquire** — inspect the narrowest target likely to change the next task decision, at the lowest sufficient fidelity.
5. **Check** — after useful evidence, `STOP` if material claims are covered; otherwise take one `EXPAND`, `SPECIALIZE`, `SWITCH`, or `REOPEN` action.

## SignalVector

`N,S,Q,V,P,B`

- `N`: need context — `0|1|?`
- `S`: dominant source — `C` code, `D` document, `R` external research, `T` state/temporal conflict, `G` generic, `?` unknown
- `Q`: requirement bitset — any of `E` exact/provenance, `F` freshness, `U` unknown capability/tool, `H` retention/handoff; `-` for none
- `V`: minimum fidelity — `I` index, `S` summary, `X` extract, `R` raw, `A` auto
- `P`: progress from last context action — `1|0|?`
- `B`: optional backup source code or `-`

## Invariants

`quality > recoverability > context cost > latency`.

Never preload every specialist or modifier. Never expand because context is merely available. A wrong source guess is recoverable: stop the branch, try one backup, then `G`. Preserve a route back to raw truth when compression or offload is used. Count reacquisition as cost.
