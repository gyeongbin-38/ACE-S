# ACE-S Design

ACE-S treats context selection as a **control problem**, not a fixed retrieval recipe.

The public skill is deliberately small: it selects a strategy, loads only the relevant specialist guidance, and stops retrieval once evidence is sufficient.

## Controller model

```text
Task
 │
 ▼
Activation Gate ── sufficient ─────────────► Solve
 │ insufficient
 ▼
Problem Router
 │
 ├─ CODE ─────────► structural seed / symbol / tests
 ├─ RESEARCH ─────► authoritative sources / claim evidence
 ├─ TEMPORAL ─────► current vs superseded state
 ├─ PLAN ─────────► future-utility retention
 ├─ HIGH-RISK ────► exact evidence / provenance
 └─ GENERIC ──────► Resolution Ladder
 │
 ▼
Resolution Ladder
index → summary → extract → raw
 │
 ▼
Sufficiency Gate
 │
 ├─ enough ───────► Verify → Solve
 └─ not enough ───► expand one narrow step ──┐
                                             └── loop
```

## Core policy

1. **Activation gate** — no retrieval is a valid action.
2. **Route** — classify the context problem before choosing a retrieval strategy.
3. **Smallest useful scope** — exact path/symbol/entity/index before broad context.
4. **Resolution ladder** — index/metadata → summary → extract → raw evidence.
5. **Specialist route** — load only the route needed for the task.
6. **Sufficiency gate** — expand on unresolved uncertainty, not just token pressure.
7. **Verification** — re-open fidelity-critical evidence before finalizing.

## Coding route learned from the repo replay

The Popular Repo Replay reinforced a specific pattern:

```text
GLOBAL SEARCH
     │
     ├─ no result → remove descriptive noise → exact symbol
     │
     └─ useful seed
           │
           ▼
     STRUCTURAL LOCALITY
     test / import / sibling / module / dependency
           │
           ▼
     exact implementation
           │
           ▼
          STOP
```

The controller should switch from global retrieval to **local structural traversal as soon as a useful seed exists**.

## Why modular references?

A monolithic context skill creates its own context overhead. ACE-S therefore applies progressive disclosure to itself:

```text
SKILL.md        small router
   │
   ├─ coding.md
   ├─ temporal.md
   ├─ research.md
   ├─ plan-aware.md
   ├─ resolution-ladder.md
   └─ evidence-and-provenance.md
```

Unrelated specialist files should not be loaded.

## Quality constraint

Optimization is valid only when quality does not regress against a comparable baseline.

```text
Quality(adaptive) >= Quality(baseline)
```

Token reduction alone is not success.

The practical priority is:

```text
correctness & completeness
        > provenance & recoverability
        > context efficiency
        > latency
```

## Public Skill vs Runtime

ACE-S is the portable **policy layer**.

Persistent event stores, bitemporal state, graph indexes, learned routing, and external memory adapters belong in an optional runtime/backend layer.

```text
                     ACE-S
              strategy controller
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
 context-router      Ratel        Acontext/xMemory
 code context      capabilities       memory
       │              │              │
       └──────────────┼──────────────┘
                      ▼
                   memahead
               plan compression
```

The goal is not to rebuild every specialized context system. The long-term architecture is to make ACE-S good at **choosing which specialized mechanism is worth using for the current task**.
