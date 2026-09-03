#!/usr/bin/env python3
"""Construct source-only candidate witnesses for fresh Suite A v0.2.

This builder never imports or executes the v0.6 retrieval/evidence controller.
It only checks out pinned repositories, verifies expected production files,
locates predeclared source anchors, records Git blob SHAs, and emits candidate
regions plus source snippets for human audit. The output must be reviewed and
committed as a sealed manifest before first policy evaluation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters"))

import deterministic_repo_localization as base  # noqa: E402

SPEC = ROOT / "benchmarks/runtime-traces/pilots/repo-behavior-witness-suite-a-v0.2-construction.json"


def git_blob_sha(repo: Path, path: str) -> str:
    cp = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"], cwd=repo, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr[-1000:])
    return cp.stdout.strip()


def region_for(lines: list[str], line: int) -> tuple[int, int]:
    # Candidate only. Human review decides final witness boundaries.
    return max(1, line - 5), min(len(lines), line + 8)


def resolve(task: dict) -> dict:
    repo = base.ensure_repo(task["repository"], task["commit_sha"])
    path = task["expected_file"]
    source = repo / path
    if not source.is_file():
        raise RuntimeError(f"missing expected file: {task['task_id']} {path}")
    lines = source.read_text(encoding="utf-8", errors="replace").splitlines()

    anchors = []
    for anchor in task["anchors"]:
        occurrences = [i for i, text in enumerate(lines, 1) if anchor in text]
        if len(occurrences) != 1:
            raise RuntimeError(
                f"anchor must be unique for {task['task_id']}: {anchor!r} -> {occurrences}"
            )
        line = occurrences[0]
        start, end = region_for(lines, line)
        snippet = [
            {"line": n, "text": lines[n - 1]}
            for n in range(start, end + 1)
        ]
        anchors.append({
            "anchor": anchor,
            "line": line,
            "candidate_start_line": start,
            "candidate_end_line": end,
            "snippet": snippet,
        })

    return {
        "task_id": task["task_id"],
        "repository": task["repository"],
        "commit_sha": task["commit_sha"],
        "prompt": task["prompt"],
        "expected_file": path,
        "source_blob_sha": git_blob_sha(repo, path),
        "anchors": anchors,
    }


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec.get("status") != "construction_before_first_policy_evaluation":
        raise RuntimeError("construction spec status mismatch")
    tasks = spec.get("tasks", [])
    if len(tasks) != 6:
        raise RuntimeError(f"expected 6 tasks, got {len(tasks)}")
    resolved = [resolve(task) for task in tasks]
    print(json.dumps({
        "suite_id": spec["suite_id"],
        "status": "candidate_witnesses_for_human_audit_before_first_policy_evaluation",
        "policy_executed": False,
        "tasks": resolved,
        "claim_boundary": (
            "Source-label construction only. No retrieval, frontier, Behavior Window, "
            "semantic judge, expected-result scoring, or policy tuning was executed."
        ),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
