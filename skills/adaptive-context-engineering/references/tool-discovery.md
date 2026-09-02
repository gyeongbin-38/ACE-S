# Tool Discovery

Use this reference only after ACE-S has already identified the context problem and the required capability is still unknown.

## Goal

Find the **smallest suitable capability** without loading every tool description or implementation.

## Procedure

1. State the required operation in one line: e.g. search repository symbols, read a PDF page, query current web state, inspect a connected source.
2. Inspect capability names/descriptions or another compact index first.
3. Keep only a small candidate set that can perform the operation.
4. Select the narrowest capability that satisfies source/access/fidelity requirements.
5. Open deeper tool documentation only when arguments, permissions, or output semantics remain unclear.
6. Return to the domain policy after the capability is selected.

## Avoid

- enumerating or reading every available tool “for awareness”;
- treating tool discovery as the primary task domain;
- opening source/implementation bodies before capability metadata is insufficient;
- carrying full tool catalogs into later model calls after selection.
