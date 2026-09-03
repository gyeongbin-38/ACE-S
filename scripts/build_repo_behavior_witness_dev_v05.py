#!/usr/bin/env python3
"""Build a reviewed development Behavior Witness manifest from frozen source.

This is a label-construction utility, not a controller. It never executes the
Behavior Window policy. For each already-observed development task it resolves
the corrected expected file at the frozen repository commit, locates the
existing expected anchor, and freezes a narrow multi-line source region around
the most behavior-relevant occurrence.

The generated manifest must be inspected and committed before it is used by the
minimality search. That separation prevents policy output from influencing the
witness boundaries.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

import deterministic_repo_localization as base  # noqa: E402

DEVSETS = [
    ROOT / "benchmarks/runtime-traces/pilots/repo-evidence-dev-v0.3-corrected.json",
    ROOT / "benchmarks/runtime-traces/sealed/repo-frontier-unseen-v0.1.json",
]

STOP = {
    "locate", "production", "source", "file", "responsible", "implementing",
    "implements", "implementation", "return", "most", "relevant", "path",
    "when", "where", "that", "this", "with", "from", "into", "using",
    "including", "used", "behavior", "configuration", "request", "requests",
}

DEF_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+\w+"),
    re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?\w+"),
    re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+\w+"),
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+\w+"),
    re.compile(r"^\s*(?:public|private|protected|static|final|synchronized|abstract|default|override|@Override|\s)+[^;{}]*\w+\s*\([^;]*\)\s*(?:\{|throws|$)"),
]


def load_tasks() -> list[dict]:
    tasks: list[dict] = []
    for path in DEVSETS:
        tasks.extend(json.loads(path.read_text(encoding="utf-8"))["tasks"])
    return tasks


def is_definition(line: str) -> bool:
    return any(p.search(line) for p in DEF_PATTERNS)


def is_comment(line: str) -> bool:
    return line.strip().startswith(("#", "//", "/*", "*", "///", '"""', "'''"))


def prompt_terms(prompt: str) -> set[str]:
    return {
        t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", prompt)
        if t.lower() not in STOP
    }


def occurrence_score(lines: list[str], lineno: int, anchor: str, terms: set[str]) -> tuple:
    lo = max(1, lineno - 10)
    hi = min(len(lines), lineno + 12)
    nearby = "\n".join(lines[lo - 1:hi]).lower()
    line = lines[lineno - 1]
    lexical = sum(1 for t in terms if t in nearby)
    definition = 1 if is_definition(line) else 0
    preceding_definition = 0
    for n in range(lineno, max(0, lineno - 8), -1):
        if is_definition(lines[n - 1]):
            preceding_definition = 1
            break
    anchor_tokens = [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_]+", anchor)]
    anchor_in_definition = 1 if definition and any(t in line.lower() for t in anchor_tokens) else 0
    non_comment = 0 if is_comment(line) else 1
    # Prefer an exact defining occurrence when available, then the occurrence
    # whose local source neighborhood best matches the task semantics.
    return (anchor_in_definition, definition, lexical, preceding_definition, non_comment, -lineno)


def resolve_task(task: dict) -> dict:
    repo = base.ensure_repo(task["repository"], task["commit_sha"])
    expected = task["expected_file"]
    source = repo / expected
    if not source.is_file():
        raise RuntimeError(f"expected file missing for {task['task_id']}: {expected}")
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
    anchor = task["expected_anchor"]
    needle = anchor.lower()
    occurrences = [i for i, line in enumerate(lines, 1) if needle in line.lower()]
    if not occurrences:
        raise RuntimeError(f"anchor not found for {task['task_id']}: {anchor!r} in {expected}")

    terms = prompt_terms(task["prompt"])
    best_line = max(occurrences, key=lambda n: occurrence_score(lines, n, anchor, terms))
    line = lines[best_line - 1]

    if is_definition(line):
        start = max(1, best_line - 1)
        end = min(len(lines), best_line + 11)
        minimum = min(6, end - start + 1)
        kind = "implementation"
    elif is_comment(line):
        start = max(1, best_line - 1)
        end = min(len(lines), best_line + 8)
        minimum = min(5, end - start + 1)
        kind = "comment_contract"
    else:
        start = max(1, best_line - 3)
        end = min(len(lines), best_line + 5)
        minimum = min(5, end - start + 1)
        kind = "implementation"

    claim = task["prompt"].split(" Return the most relevant production file path.")[0].strip()
    return {
        "task_id": task["task_id"],
        "repository": task["repository"],
        "commit_sha": task["commit_sha"],
        "prompt": task["prompt"],
        "expected_file": expected,
        "expected_anchor": anchor,
        "anchor_occurrences": occurrences,
        "selected_anchor_line": best_line,
        "witnesses": [
            {
                "path": expected,
                "start_line": start,
                "end_line": end,
                "kind": kind,
                "claim": claim,
                "minimum_visible_lines": minimum,
            }
        ],
        "construction_note": (
            "Development-label witness resolved from corrected expected_file/expected_anchor "
            "before Behavior Window minimality execution. The witness interval is source-location "
            "evidence only; claim text is documentation and is not passed to the scorer."
        ),
    }


def main() -> None:
    tasks = [resolve_task(t) for t in load_tasks()]
    out = {
        "schema_version": "0.5-dev",
        "suite_id": "repo-behavior-witness-development-v0.5",
        "status": "generated_for_review_before_minimality_controller_execution",
        "source_tasksets": [str(p.relative_to(ROOT)).replace("\\", "/") for p in DEVSETS],
        "tasks": tasks,
        "scoring_contract": {
            "hard_gate": "all 14 expected files must be in frontier and each frozen witness must satisfy minimum_visible_lines overlap",
            "claim_is_scorer_input": False,
            "anchor_is_scorer_input": False,
        },
        "claim_boundary": (
            "Already-observed development repositories only. This manifest is for minimum-policy "
            "selection and cannot establish unseen generalization."
        ),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
