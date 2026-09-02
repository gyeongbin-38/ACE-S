# TOOLS Manifest

## Load only when

The context problem is understood but the smallest suitable capability/source interface is not yet known.

## Do not load when

- an appropriate tool/source is already known and available;
- tool selection is irrelevant to the answer;
- the task can be solved directly from current context.

## Entry action

Inspect capability metadata/index first. Do not open implementation/source bodies merely to decide which tool can perform the needed operation.

Typical entry fidelity: `INDEX`.

## Open next

If this modifier is material, read only `references/tool-discovery.md`.
